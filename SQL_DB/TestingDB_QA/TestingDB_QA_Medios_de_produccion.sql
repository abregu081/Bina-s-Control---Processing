-- MySQL dump 10.13  Distrib 8.0.36, for Linux (x86_64)
--
-- Host: localhost    Database: TestingDB_QA
-- ------------------------------------------------------
-- Server version	8.0.44-0ubuntu0.24.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Medios_de_produccion`
--

DROP TABLE IF EXISTS `Medios_de_produccion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Medios_de_produccion` (
  `ID_Medios_de_produccion` int NOT NULL AUTO_INCREMENT,
  `Nombre` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `Descripcion` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `Linea_produccion_id` int NOT NULL,
  PRIMARY KEY (`ID_Medios_de_produccion`),
  KEY `Linea_produccion_id` (`Linea_produccion_id`),
  CONSTRAINT `Medios_de_produccion_ibfk_1` FOREIGN KEY (`Linea_produccion_id`) REFERENCES `Lineas_de_produccion` (`ID_Lineas_de_produccion`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Medios_de_produccion`
--

LOCK TABLES `Medios_de_produccion` WRITE;
/*!40000 ALTER TABLE `Medios_de_produccion` DISABLE KEYS */;
INSERT INTO `Medios_de_produccion` VALUES (1,'ManualInspection','Estacion de testeo manual de motrex',1),(2,'AutoTest','Medio correspondiente a un esto automatico previo a su paso por Manual Inspeccion',1),(3,'OQC','Puesto  de finalizacion de la linea productiva de Motrex',1),(4,'PCBInspeccionDCSD','Puesto de testeo de la pcb procesentes del front del equipo, previo a su paro por la dispensadora de grasa',1),(5,'ICT','Puesto Destinado a la inspeccion de 3 jigs Sub, Main y el conjunto armado',1),(6,'PCBInspeccionMAIN','ICT ubicada en la zona de ensamblaje de motrex',1),(8,'LADCMAFT','Medio AFT-LADCM ubicado en UNAE1',2),(9,'RUNIN','Medio RUNIN-LADCM ubicado en UNAE1-Con Supernova',2);
/*!40000 ALTER TABLE `Medios_de_produccion` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-08 19:39:40
