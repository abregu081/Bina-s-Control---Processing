# Modulo de Captura de Logs Formato-Mirgor para entrenamiento de un MiniModelo


# Detalles:
1. Esta rama es la para los logs especiales de la dcm
2. Cambio principal, no se agrega el 0 como carater debido a que ya cuenta el log con  el mismo. 
            box_value = f"{box_crudo}" if box_crudo else "" #Cuidado aca si nuesto log tiene JIG : 08
3. Si no lo tuviera habria que cambiarlo
            
## Notas:
1. Este es un reversionado de la primeras versiones de 2025 Realizado en mis practicas
2. Se optimiza para su acoplamiento junto con grafa y powerBI
3. Se apunta a su integracion con el modelo de gestion Bina's Control
4. Se agrega el concepto de Lake

## Version Vieja de Produccion
| Medio | Version_Vieja | Version_Factorizada |
|-------|---------------|---------------------|
| ManualInspection | 1.2 | 1.0.1 |
| AutoTest | 1.2 | 1.0.1 |
| OQC | 1.2 | 1.0.1 |
| PCBInspeccionDCSD | 1.2 | 1.0.1 |
| ICT | 1.2 | 1.0.1 |
| PCBInspeccionMAIN | 1.2 | 1.0.1 |
| LADCMAF | 1.2 | 1.0.1 |
| RUNIN | 1.2 | 1.0.1 |
