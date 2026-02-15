

insert into testingdb_qa.unidad_de_negocio select * from testingdb.unidad_de_negocio;
insert into testingdb_qa.lineas_de_produccion select * from testingdb.lineas_de_produccion;
insert into testingdb_qa.medios_de_produccion select * from testingdb.medios_de_produccion;
insert into testingdb_qa.token select * from testingdb.token;
insert into testingdb_qa.registros select * from testingdb.registros;
 
#DB Original
#----------------------------------------------------
#Unidad_de_negocio
#select * from testingdb.unidad_de_negocio;
# (idUnidad_de_negocio , nombre , sector , descripcion)

#Linea de produccion
#select * from testingdb.lineas_de_produccion
#(idLineas_de_produccion,linea ,ubicacion,unidad_de_negocio_id)

#medios_de_produccion
#select * from testingdb.medios_de_produccion
#(id_medios_de_produccion,nombre,descripcion ,linea_produccion_id)

#Token
#Select * from testingdb.token
#(Idtoken,token,tipo,date,estado,medio_id)

#registros
#(idregistros , fecha, hora , modelo , serial , resultado , detalle , medio, hostname , planta , banda , box, imei , sku, testtime , runtime , modelfile , medio_id)

#Servicio
#(id , fecha, hora , hostname, estacion, linea , medio_id )
#----------------------------------------

#insert into TestingDB_QA.Lineas_de_produccion select * from testingdb.lineas_de_produccion;