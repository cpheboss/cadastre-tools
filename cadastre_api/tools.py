from pathlib import Path
from shapely.geometry import Polygon
import os
import zlib
import requests
import geojson
import webbrowser

def get_parcelles_file(code_departement, code_ville, dir='.'):
    filename = 'cadastre-{ville}-parcelles.json'.format(ville=code_ville)
    file = '{dir}/{file}'.format(dir=dir, file=filename)
    return file

def parcelles_file_exist(code_departement, code_ville, dir='.'):
    file = get_parcelles_file(code_departement, code_ville, dir)
    return os.path.isfile(file)

def download_parcelles_file(code_departement, code_ville, output_dir='.'):
    # Create dir if needed
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    filename = 'cadastre-{ville}-parcelles.json'.format(ville=code_ville)
    file = '{dir}/{file}'.format(dir=output_dir, file=filename)
    address='https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/{dpt}/{ville}/{file}.gz'
    address=address.format(dpt=code_departement, ville=code_ville, file=filename)

    res = requests.get(address)

    if not res.ok:
        raise res.reason

    with open(file, 'w') as f:
        f.write(zlib.decompress(res.content, 16+zlib.MAX_WBITS).decode('utf-8'))
    
    return file

def get_code_ville(departement, ville):
    address = 'https://geo.api.gouv.fr/communes?nom={nom}&codeDepartement={dpt}&fields=nom,code'
    address = address.format(nom=ville, dpt=departement)
    res = requests.get(address, headers={'Accept':'application/json'})

    if not res.ok:
        raise res.reason
    
    data = res.json()
    if len(data) < 1:
        raise Exception("Ville non trouvée")
    if len(data) > 1:
        raise Exception("Plusieurs villes trouvées")
    
    return data[0]['code']

def get_parcelles(departement, ville, parcelles_dir):
    ville_insee = get_code_ville(departement, ville)

    if not parcelles_file_exist(departement, ville_insee, parcelles_dir):
        file = download_parcelles_file(departement, ville_insee, parcelles_dir)
    else:
        file = get_parcelles_file(departement, ville_insee, parcelles_dir)
    
    with open(file, 'r') as f:
        parcelles = geojson.load(f)

    return parcelles

def get_parcelles_with_contenance(departement, ville, contenance, parcelles_dir):
    parcelles = get_parcelles(departement, ville, parcelles_dir)
    parcelles = [x for x in parcelles['features'] if 'contenance' in x['properties'] and x['properties']['contenance']==contenance]
    return parcelles

def get_parcelle_representative_point(geojson_polygon):
    pol=Polygon(geojson_polygon['geometry']['coordinates'][0]).representative_point()
    return [pol.x, pol.y]

def get_adresse(lon, lat):
    address = 'https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}'
    address = address.format(lon=lon, lat=lat)
    res = requests.get(address)
    return res.json()

def get_adresses(dpt, ville, contenance, parcelles_dir):
    parcelles = get_parcelles_with_contenance(dpt, ville, contenance, parcelles_dir)
    points = [get_parcelle_representative_point(x) for x in parcelles]
    adresses = [get_adresse(*p) for p in points]
    return adresses

def open_adresse_in_maps(adresse):
    address = "https://www.google.fr/maps/place/{adr}"
    webbrowser.open(address.format(adr=adresse), new=2)

def get_label_from_adresse(adresse):
    return adresse['features'][0]['properties']['label']

def do_it_all(departement, ville, contenance, parcelles_dir="./data/json/"):
    adresses = get_adresses(departement, ville, contenance, parcelles_dir)
    for a in adresses:
        open_adresse_in_maps(get_label_from_adresse(a))