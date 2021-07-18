# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject
from qgis.core import QgsVectorLayer
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
        self.Communes_list = []
        pass

    def newLayer(self, oldlayer, CRS, iface):

        self.features = oldlayer.getFeatures()
        print(self.features)    

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
            self.vl.updateFields()

        #set new layer Features
        self.f = QgsFeature()

        #Perform further actions
        #self.geometry()
        self.addFeatures(oldlayer)

        #Create the new layer
        QgsProject.instance().addMapLayer(self.vl)


        #Restart List
        self.Communes_list = []

        #Remove files
        #self.delete_layers()

        #check layers
        #self.check_layers()


        
        
    
    def addFeatures(self, oldlayer):
        for feature in self.features :
            self.Geometry(feature, oldlayer)
            #print(feature.attributes()[0])
            #print(len(feature.attributes()))
            self.f.setAttributes(feature.attributes())
            self.pr.addFeature(self.f)
            self.vl.updateExtents()
        
        ##HERE
        point_features = self.vl.getFeatures()
        self.find_point_polygon(point_features)
            

        pass

    def Geometry(self, feature, oldlayer) :
        GEOMETRY = feature.geometry()
        #print(GEOMETRY)
        #print('old coordinates :', ('%f, %f' % (GEOMETRY.asPoint().x(), GEOMETRY.asPoint().y())))
        X = GEOMETRY.asPoint().x()
        Y = GEOMETRY.asPoint().y()
        #self.f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(10,10)))
        xform = QgsCoordinateTransform(oldlayer.crs(), QgsCoordinateReferenceSystem(4326), QgsProject.instance())
        point = xform.transform(QgsPointXY(X, Y))
        self.f.setGeometry(QgsGeometry.fromPointXY(point))

        coordinate= self.f.geometry().asPoint()
        self.X = coordinate[0]
        self.Y = coordinate[1]
        self.getCommune()
        pass
        
    def getCommune(self) :
        file_path = (base_path / "./XY_ref/communes_XYmax.csv").resolve()
        with open(file_path, 'r+') as csvCommunes :
            for Commune in csvCommunes :
                Commune_list = Commune.split(',')
                if self.X >= float(Commune_list[1]) and self.X < float(Commune_list[2]) and self.Y >= float(Commune_list[3]) and self.Y < float(Commune_list[4]) :
                    if Commune_list[0] not in self.Communes_list :
                        self.Communes_list.append(Commune_list[0])
                        print('les communes sont: ', self.Communes_list)
                        self.get_file(Commune_list[0])
                else :
                    continue
        pass
    
    def get_file(self, commune_code) :
        url = "https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/" + commune_code[0:2] + "/" + commune_code + "/cadastre-" + commune_code + "-parcelles.json.gz"
        
        file_name = 'cadastre-' + commune_code + '-parcelles.json.gz'
        unzip_file_name = 'cadastre-' + commune_code + '-parcelles.json'
        file_path = (base_path / f"./layers/{file_name}").resolve()
        unzip_file_path = (base_path / f"./layers/{unzip_file_name}").resolve()
        with urllib.request.urlopen(url) as response, open(file_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        
        input = gzip.GzipFile(file_path, 'rb')
        s = input.read()
        input.close()

        output = open(unzip_file_path, 'wb')
        output.write(s)
        output.close()

        os.remove(file_path)
        pass

    def delete_layers(self) :
        file_path = (base_path / "./layers/").resolve()
        for f in os.listdir(file_path) :
            file_path_f = (base_path / f"./layers/{f}").resolve()
            to_remove = f'{file_path_f}'
            os.remove(to_remove)
        pass

    def check_layers(self) :
        file_path = (base_path / "./layers/").resolve()
        for f in os.listdir(file_path) :
            f_list = f.split('-')
            commune_code = f_list[1]
            print(commune_code)
            self.Communes_list.append(commune_code)            
        pass


    def find_point_polygon(self, point_Layer) :
        file_name = 'cadastre-24437-parcelles.json'
        file_path = (base_path / "./layers/cadastre-24037-parcelles.json").resolve()

        #vlayer = self.iface.addVectorLayer(f"{file_path}", "essai", "ogr")
        vlayer = QgsVectorLayer(f"{file_path}", "essai", "ogr")
        #QgsProject.instance().addMapLayer(vlayer)

        ############""


        vlayer_features = vlayer.getFeatures()

        point_List = []
        for point in point_Layer :
            point_List.append(point.geometry())
       
        for i in vlayer_features :
            #print(i.attributes())
            #print(i.geometry())
            for point in point_List :
                #if point.geometry().within(i.geometry()) :
                if i.geometry().contains(point) :
                    print("waou man")
                    print(i.attributes())

        if not vlayer:
            print("Layer failed to load!")
        else :
            print('hulala')





        """
        vl = QgsVectorLayer("Point", "temp", "memory")
        pr = vl.dataProvider()
        pr.addAttributes([QgsField("name", QVariant.String),
            QgsField("age",  QVariant.Int),
            QgsField("size", QVariant.Double)])
        vl.updateFields()
        """
