import streamlit as st
import geopandas as gpd
import os
import psycopg2
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import base64
from io import StringIO
import shutil
from streamlit_folium import folium_static
import folium

engine = create_engine('*******', echo=True)

def calcul(shapefiles):
    if len(shapefiles)>0:
        for shapefile in shapefiles:
            shapefile.seek(0)
            with open(shapefile.name, 'wb') as f:
                shutil.copyfileobj(shapefile, f, length=131072)
            if os.path.splitext(shapefile.name)[1] in ['.shp', '.geojson', '.gpkg']:
                var = shapefile.name
    else:
        var = "qp_bdtopo_com_75056_2020.shp"

    sdf = gpd.read_file(var)
    sdf['identifiant_geo'] = np.arange(sdf.shape[0])
    sdf3035 = sdf.to_crs("EPSG:3035")
    str_geometry = ','.join(sdf3035.geometry.astype(str))
    
    temp = []
    for i in range(sdf3035.shape[0]):
        temp.append("(select 'SRID=3035;" + sdf3035.geometry.astype(str)[i] +"'::geometry,"+str(i)+" as identifiant_geo)")
         
    request = "select x.identifiant_geo, x.geometry , round(sum(x.men)) as menages, round(sum(x.ind)) as population,"\
    "round(sum(x.men_pauv*x.pond)) as menages_pauvres,"\
    "round(sum(x.men_fmp*x.pond)) as familles_monoparentales,"\
    "round(sum(x.men_5ind*x.pond)) as familles_nombreuses,"\
    "round(sum(x.ind_snv*x.pond) / sum(x.ind*x.pond)) as niveau_de_vie_moyen,"\
    "round(sum(x.men_coll*x.pond)) as menages_en_logement_collectif,"\
    "round(sum(x.men_mais*x.pond)) as menages_en_maison_individuelle,"\
    "round(sum(x.log_soc*x.pond)) as logements_sociaux,"\
    "round(sum(x.log_av45*x.pond)) as logements_construits_avant_1945,"\
    "round(sum(x.log_45_70*x.pond)) as logements_construits_entre_1945_1970,"\
    "round(sum(x.log_70_90*x.pond)) as logements_construits_entre_1970_1990,"\
    "round(sum(x.log_ap90*x.pond)) as logements_construits_apres_1990,"\
    "round(sum(x.men_1ind*x.pond)) as menages_1_personne,"\
    "round(sum(x.ind_0_10*x.pond)) as population_moins_10ans,"\
    "round(sum(x.ind_11_17*x.pond)) as population_11_17_ans,"\
    "round(sum(x.ind_65p*x.pond)) as population_plus_65_ans,"\
    "round(sum(x.ind_80p*x.pond)) as population_plus_80_ans,"\
    "round(sum(x.men_prop*x.pond)) as menages_proprietaires "\
    " from "\
    "(select *, st_area(st_intersection(f.geom, t.geometry))/st_area(t.geometry) as pond   "\
    " from filosofi_3035_full f, (" + 'UNION'.join(temp)  + ") t where st_intersects(f.geom, t.geometry)) as x group by x.identifiant_geo,x.geometry"  
    
    test = gpd.read_postgis(request, engine, geom_col='geometry')
    test = sdf.merge(test.drop('geometry', axis=1), on='identifiant_geo')

    stest = test.to_crs('EPSG:4326')
    sextent = stest.total_bounds
    return([test.drop('geometry', axis=1), stest])

st.title('GridInShape')
st.markdown('''L'application GridInShape projete les données carroyées [Filosofi 2015 de l'Insee](https://www.insee.fr/fr/statistiques/4176305) sur un fond choisi par l'utilisateur. Les calculs sont effectués au prorata des surfaces communes entre les carreaux et les territoires de l'utilisateurs. L'application accepte les formats ESRI Shapefile, geojson et Geopackage.''')
shapefiles = st.file_uploader('Choisir le fond de carte',accept_multiple_files=True)
    
res = calcul(shapefiles)    
m = folium.Map()
Y1, X1, Y2, X2 = res[1].total_bounds
folium.GeoJson(res[1].to_json(), name="geojson", popup=folium.GeoJsonPopup(fields=['identifiant_geo'])).add_to(m)
m.fit_bounds([[X1, Y1],[X2,Y2]])
folium_static(m)

st.dataframe(res[0])
csv = res[0].to_csv(index=False)
b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
href = f'<a href="data:file/csv;base64,{b64}">Télécharger en CSV les résultats</a> (clic droit et exporter &lt; sous &gt;.csv)'
st.markdown(href, unsafe_allow_html=True)


