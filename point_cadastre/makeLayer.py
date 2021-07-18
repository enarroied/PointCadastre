# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QVariant
from qgis.core import * 
import os.path
from pathlib import Path
import urllib.request
import shutil
import gzip
import os

base_path = Path(__file__).parent

class MakeLayer :
    def __init__(self):
        #list of all commune file contained in "layers" directory
        self.Communes_list = []

    def newLayer(
                    self, 
                    oldlayer, 
                    progressBar, 
                    textBrowser_main,
                    checkBox_colonnes,
                    checkBox_Communes,
                    checkBox_INSEE,
                ):
        
        self.checkBox_colonnes = checkBox_colonnes
        self.checkBox_Communes = checkBox_Communes
        self.checkBox_INSEE = checkBox_INSEE

        #ProressBar item to increase the progressBar and textBrowser to display messages
        self.progressBar = progressBar
        self.textBrowser_main = textBrowser_main
        self.textBrowser_main.setText('Vérification des données en cours...')

        #Get the fields of selected layer and append to lists for further use
        self.features = oldlayer.getFeatures()
        new_layer_field_names = []
        new_layer_field_types = []
        for field in oldlayer.fields() :
            new_layer_field_names.append(field.name())
            new_layer_field_types.append(field.type())
        
        #Create Temporary Layer
        self.vl = QgsVectorLayer("Point?crs=epsg:4326", "temp", "memory")
        self.pr = self.vl.dataProvider()

        #Create the fields for the new layer, oldlayer + new ones (cadastre layers)
        for i in range (0, len(new_layer_field_names) ) :
            att = [QgsField(new_layer_field_names[i], new_layer_field_types[i])]
            self.pr.addAttributes(att)

        #Here add new fields depending on checked attributes
        atrribute_list=[]
        if self.checkBox_colonnes.isChecked() :
            atrribute_list = atrribute_list + [
                              QgsField("Departement", QVariant.String),
                              QgsField("Commune", QVariant.String), 
                              QgsField("Prefixe", QVariant.String),
                              QgsField("Section", QVariant.String),
                              QgsField("Parcelle", QVariant.String)  
                              ]
        if self.checkBox_INSEE.isChecked() :
            atrribute_list = atrribute_list + [
                              QgsField("Code INSEE", QVariant.String)
                              ]

        if self.checkBox_Communes.isChecked() :
            atrribute_list = atrribute_list + [
                              QgsField("Nom commune", QVariant.String)
                              ]

        self.pr.addAttributes(atrribute_list)

        self.vl.updateFields()

        #Increase ProgressBar
        self.progressBar.setValue(2)
        #set new layer Features
        self.f = QgsFeature()

        #check layers : if the exist, apend to self.Communes_list (so they dont need to be downloaded)
        self.check_layers()

        #Perform further actions
        self.addFeatures(oldlayer)

        #Inrease ProgressBar
        self.textBrowser_main.setText('C\'est presque fini...')
        if self.progressBar.value() < 90 : self.progressBar.setValue(90)
        

        #Create the new layer
        QgsProject.instance().addMapLayer(self.vl)

        #Restart List
        self.Communes_list = []

        self.textBrowser_main.setText('Couche générée avec succès !')

    def addFeatures(self, oldlayer):
        self.textBrowser_main.setText('Extraction des données cadastrales en cours...')
        for feature in self.features :
            #Call Gepmetry function, will duplicate the geometries of the old layer to new layer
            self.Geometry(feature, oldlayer)

            self.f.setAttributes(feature.attributes())
            self.pr.addFeature(self.f)
            self.vl.updateExtents()
            self.getCommune()

            #Inrease ProgressBar
            self.increasePG(2, 30, len(oldlayer) )
        
        # HERE append CADASTRE INFO
        point_features = self.vl
        
        # Get the CADASTRE info from polygon and if exists add to new point layer
        self.find_point_polygon(point_features)
        
    def Geometry(self, feature, oldlayer) :
        #Get the geometry from oldlayer
        GEOMETRY = feature.geometry()
        X = GEOMETRY.asPoint().x()
        Y = GEOMETRY.asPoint().y()

        #Transform oldlayer's point Geometry from oldelayer CRS to EPSG 4326
        #Reason for this is cadastre layers in GeoJson format come in 4326
        xform = QgsCoordinateTransform(oldlayer.crs(), QgsCoordinateReferenceSystem(4326), QgsProject.instance())
        point = xform.transform(QgsPointXY(X, Y))
        self.f.setGeometry(QgsGeometry.fromPointXY(point))

        #Get X,Y coordinates as 4326 so the communes where this points are can be guessed
        coordinate= self.f.geometry().asPoint()
        self.X = coordinate[0]
        self.Y = coordinate[1]     
        
    def getCommune(self) :
        #Get a list of possible communes for each point of the point layer
        file_path = (base_path / "./XY_ref/communes_XYmax.csv").resolve()
        with open(file_path, 'r+') as csvCommunes :
            for Commune in csvCommunes :
                Commune_list = Commune.split(',')
                if Commune_list[0] not in self.Communes_list :
                    if self.X >= float(Commune_list[1]) and self.X < float(Commune_list[2]) and self.Y >= float(Commune_list[3]) and self.Y < float(Commune_list[4]) :
                        self.Communes_list.append(Commune_list[0])
                        self.get_file(Commune_list[0])
                else :
                    continue
    
    def get_file(self, commune_code) :
        #Create path for download and paths/file name for compressed json file
        file_name = 'cadastre-' + commune_code + '-parcelles.json.gz'
        file_path = (base_path / f"./layers/{file_name}").resolve()
        url = "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/" + commune_code[0:2] + "/" + commune_code + "/cadastre-" + commune_code + "-parcelles.json.gz"
       
        #Unzip and save the fil in directory
        unzip_file_name = 'cadastre-' + commune_code + '-parcelles.json'
        unzip_file_path = (base_path / f"./layers/{unzip_file_name}").resolve()
        with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)       
        input = gzip.GzipFile(file_path, 'rb')
        s = input.read()
        input.close()
        output = open(unzip_file_path, 'wb')
        output.write(s)
        output.close()

        #Remove the compressed file
        os.remove(file_path)

    def delete_layers(self) :
        #Delete all the Commune layers
        file_path = (base_path / "./layers/").resolve()
        for f in os.listdir(file_path) :
            file_path_f = (base_path / f"./layers/{f}").resolve()
            to_remove = f'{file_path_f}'
            os.remove(to_remove)

    def check_layers(self) :
        #Check if any Commune layer exists and evenially append to self.Communes_list = []
        file_path = (base_path / "./layers/").resolve()
        for f in os.listdir(file_path) :
            f_list = f.split('-')
            commune_code = f_list[1]
            self.Communes_list.append(commune_code)     

    def find_point_polygon(self, point_Layer) :
        #Create list of points to iterate :
        point_Layer_iterator = point_Layer.getFeatures()
        point_List = []
        for point in point_Layer_iterator :
            point_List.append(point)

        self.textBrowser_main.setText('Association des données cadastrales en cours...')
        #iterate each commune by code (eg:12345)
        for code in self.Communes_list :
            file_name = f'cadastre-{code}-parcelles.json'
            file_path = (base_path / f"./layers/{file_name}").resolve()

            #Crate a temporary layer for processing - Layer is polygons of cadastre --> commune(defined by code)
            vlayer = QgsVectorLayer(f"{file_path}", f"{file_name}", "ogr")
            if not vlayer.isValid():
                print ("Layer failed to load!")
            vlayer_features = vlayer.getFeatures()

            #Iterate the point list for each Cadastre polygon -- see if point is within it and if so append data :

            for i in vlayer_features :
                for point in point_List :
                    if point.geometry().within(i.geometry()) :

                        if self.checkBox_colonnes.isChecked() :
                            if i.attributes()[1][:2] != '97' :
                                point_field_Departement = point.fieldNameIndex('Departement')
                                point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_Departement:i.attributes()[1][:2]}})
                                point_Layer.updateExtents()
                            else :
                                point_field_Departement = point.fieldNameIndex('Departement')
                                point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_Departement:i.attributes()[1][:3]}})
                                point_Layer.updateExtents()

                            point_field_Commune = point.fieldNameIndex('Commune')
                            point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_Commune:i.attributes()[1]}})
                            point_Layer.updateExtents()

                            point_field_Prefixe = point.fieldNameIndex('Prefixe')
                            point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_Prefixe:i.attributes()[2]}})
                            point_Layer.updateExtents()

                            point_field_Sectiion = point.fieldNameIndex('Section')
                            point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_Sectiion:i.attributes()[3]}})
                            point_Layer.updateExtents()

                            point_field_Parcelle = point.fieldNameIndex('Parcelle')
                            point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_Parcelle:i.attributes()[0][-4:]}})
                            point_Layer.updateExtents()

                        if self.checkBox_INSEE.isChecked() :
                            point_field_INSEE = point.fieldNameIndex('Code INSEE')
                            point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_INSEE:i.attributes()[0]}})
                            point_Layer.updateExtents()

                        if self.checkBox_Communes.isChecked() :
                            with open(base_path / './XY_ref/communes_XYmax.csv', 'r+') as read_communes :
                                for communes in read_communes: 
                                    commune = communes.split(',')
                                    if i.attributes()[1] == commune[0] :
                                        point_field_nom_commune = point.fieldNameIndex('Nom commune')
                                        point_Layer.dataProvider().changeAttributeValues({point.id():{point_field_nom_commune:commune[-1]}})
                                        point_Layer.updateExtents()
                            read_communes.close()

            #Increase progress Bar :
            self.increasePG(30, 98, len(self.Communes_list))

    def increasePG(self, Value, Value_max, Length) :
        #Increase progress Bar :
        Increase_value = int( (Value_max - Value) / (Length + 1) ) #+1 to avoid div by 0
        if Increase_value == 0 : 
            Increase_value = 1
        if self.progressBar.value() < Value_max :
            self.progressBar.setValue(self.progressBar.value() + Increase_value)
    
    def update_communes(self) :
        #Update the info of communes

        #Get and unzip file (and remove compressed file) :

        #Path for dowloaded and compressed communes layer :
        file_path_communes_compressed = (base_path / "./XY_ref/cadastre-france-communes.json.gz").resolve()
        #Path for uncompressed communes layer :
        file_path_communes = (base_path / "./XY_ref/cadastre-france-communes.json").resolve()

        url = 'https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/france/cadastre-france-communes.json.gz'
        with urllib.request.urlopen(url) as response, open(file_path_communes_compressed, 'wb') as out_file:
            shutil.copyfileobj(response, out_file) 
        input = gzip.GzipFile(file_path_communes_compressed, 'rb')
        s = input.read()
        input.close()
        output = open(file_path_communes, 'wb')
        output.write(s)
        output.close()
        #Remove the compressed file
        os.remove(file_path_communes_compressed)

        #Generate the XYmins and max file :
        i=0
        with open(file_path_communes, 'r+') as communes, open(base_path / './XY_ref/communes_XYmax_2.csv', 'w+') as communes_XY:
            for commune in communes :
                if i == 0:
                    i+= 1
                    continue
                
                code_commune_list = commune.split('"id":"')
                try :
                    code_commune = code_commune_list[1][:5]
                    nom_commune_list = commune.split('"nom":"')
                    nom_commune= nom_commune_list[1].split('","')[0].split('"}')[0]
                except :
                    print(commune)
                    None
                coordinate_list = commune.split('[[[')
                
                list_X=[]
                list_Y=[]
                try :
                    coordinate_list2 = coordinate_list[1].split('],[')
                    for coordinate_couple in coordinate_list2 :
                        coordinate= coordinate_couple.split(',')
                        X = coordinate[0].replace(']', '').replace('[', '').replace('{', '').replace('}', '')
                        Y = coordinate[1].replace(']', '').replace('[', '').replace('{', '').replace('}', '')
                        list_X.append(float(X))
                        list_Y.append(float(Y))
                    list_X.sort()
                    list_Y.sort()
                    communes_XY.write(f"{code_commune}, {list_X[0]}, {list_X[-1]}, {list_Y[0]}, {list_Y[-1]}, {nom_commune}\n")                
                except :
                    None

        communes.close()
        communes_XY.close()
        print("here done !")
        
        os.remove(base_path / './XY_ref/communes_XYmax.csv')
        os.rename(base_path / './XY_ref/communes_XYmax_2.csv', base_path / './XY_ref/communes_XYmax.csv')
        os.remove(file_path_communes)
