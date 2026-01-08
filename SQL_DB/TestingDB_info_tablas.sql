

insert into TestingDB_QA.Unidad_de_negocio select * from testingdb.unidad_de_negocio;
insert into TestingDB_QA.Lineas_de_produccion select * from testingdb.lineas_de_produccion;
insert into TestingDB_QA.Medios_de_produccion select * from testingdb.medios_de_produccion;
insert into TestingDB_QA.Token select * from testingdb.token;
insert into TestingDB_QA.Registros select * from testingdb.registros;
 
#DB Original
#----------------------------------------------------
#Unidad_de_negocio
#select * from testingdb.unidad_de_negocio;
# (idUnidad_de_negocio , nombre , sector , descripcion)

#Linea de produccion
#select * from testingdb.lineas_de_produccion
#(idLineas_de_produccion,linea ,ubicacion,unidad_de_negocio_id)

#Medios_de_produccion
#Select * from testingdb.medios_de_produccion
#(idMedios_de_produccion,nombre,descripcion ,linea_produccion_id)

#Token
#Select * from testingdb.token
#(Idtoken,token,tipo,date,estado,medio_id)

#Registros
#(IDResistros , Fecha, Hora , Modelo , Serial , Resultado , Detalle , Medio, Hostname , Planta , Banda , Box, IMEI , SKU, TestTime , Runtime , ModelFile , medio_id)

#Servicio
#(id , fecha, hora , hostname, estacion, linea , medio_id )
#----------------------------------------

#insert into TestingDB_QA.Lineas_de_produccion select * from testingdb.lineas_de_produccion;