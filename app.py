from flask import Flask, request, jsonify, redirect
from pymongo import MongoClient
import uuid
import json
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)
client = MongoClient("mongodb+srv://manuel1301999:l9elnvFhFsLWMJYb@base.yzcxe.mongodb.net/keys?retryWrites=true&w=majority")
db = client.keys
keys_collection = db.keys

# Middleware de autenticación
def autenticar_solicitud():
    # Solo intercepta las solicitudes que no son OPTIONS
    if request.method != 'OPTIONS':
        token = request.headers.get('Authorization')
        if token != 'Bearer efiaf39H8G34h89eeca00ICK00D0EKF020ekcwekq-9J39FDJ0fvw-9J39FJQ9S0q0ejf2csEF9JE':
            return jsonify({'error': 'Intenta de nuevo'}), 401

@app.before_request
def verificar_autenticacion():
    return autenticar_solicitud()
@app.route('/establecer_limit/<limite>', methods=['POST'])
def establecer_limite(limite):
    try:
        limite = int(limite)
        keys_collection.update_one({"tipo": "limite_usos"}, {"$set": {"limite": limite}}, upsert=True)
        return jsonify({'mensaje': f'Límite establecido en {limite}'}), 200
    except ValueError:
        return jsonify({'error': 'El límite debe ser un número entero válido'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notificacion', methods=['POST'])
def notificacion():
    try:
        data = request.json
        notificacion = data.get('notificacion')
        telefono = data.get('telefono')

        limite = keys_collection.find_one({"tipo": "limite_usos"})
        if limite and limite.get('limite', 0) > 0:
            keys_collection.update_one({"tipo": "limite_usos"}, {"$inc": {"limite": -1}})
            enlace = f"http://app.regionhuanuco.gob.pe/soap_pruebas/sms.php?sms={notificacion}&numero={telefono}"

            # Realiza la solicitud al servicio externo desde el servidor
            response = requests.get(enlace)

            if response.status_code == 200:
                return jsonify({'message': 'Notificación enviada'}), 200
            else:
                return jsonify({'error': 'Error al enviar la notificación'}), response.status_code
        else:
            return jsonify({'error': 'Te quedaste sin créditos'}), 403

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verificar_limite', methods=['GET'])
def verificar_limite():
    try:
        limite = keys_collection.find_one({"tipo": "limite_usos"})
        if limite:
            return jsonify({'limite': limite.get('limite', 0)}), 200
        else:
            return jsonify({'error': 'Límite de usos no establecido'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# GENERAR LAS KEYS
@app.route('/generar', methods=['POST'])
def generarKey():
    try:
        key_type = request.json['tipo'] 
        if key_type not in ['A', 'B', 'C', 'D', 'E']:
            return jsonify({'error': 'Tipo de clave no válido'}), 400

        key_value = str(uuid.uuid4()).upper()
        key_doc = {
            'valor': key_value,
            'tipo': key_type,
            'estado': False,
            'autorizado': True,
            "sms": False,
            'creditos': 0
        }
        keys_collection.insert_one(key_doc)
        return jsonify({'key': key_value, 'autorizado': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ACTUALIZAR VALOR DE FALSE A TRUE
@app.route('/actualizar/<key>/<status>', methods=['PUT'])
def actualizarKey(key,status):
    try:
        if status == "1":
            estado = True
        elif status == "2":
            estado = False
        else:
            estado = False

        
        result = keys_collection.update_one(
            {'valor': key},
            {'$set': {'estado': estado}}
        )
        if result.matched_count > 0:
            return jsonify({'message': 'Estado actualizado a: '+str(estado)}), 200
        else:
            return jsonify({'message': 'Key no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ACTUALIZAR VALOR DE FALSE A TRUE
@app.route('/autorizar/<key>/<status>', methods=['PUT'])
def autorizarKey(key,status):
    try:
        if status == "1":
            autorizado = True
        elif status == "2":
            autorizado = False
        else:
            autorizado = False

        
        result = keys_collection.update_one(
            {'valor': key},
            {'$set': {'autorizado': autorizado}}
        )
        if result.matched_count > 0:
            return jsonify({'message': 'Autorizado actualizado a: '+str(autorizado)}), 200
        else:
            return jsonify({'message': 'Key no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ACTUALIZAR VALOR DE FALSE A TRUE
@app.route('/mensajes/<key>/<status>', methods=['PUT'])
def mensajesKey(key,status):
    try:
        if status == "1":
            sms = True
        elif status == "2":
            sms = False
        else:
            sms = False

        
        result = keys_collection.update_one(
            {'valor': key},
            {'$set': {'sms': sms}}
        )
        if result.matched_count > 0:
            return jsonify({'message': 'Sms actualizado a: '+str(sms)}), 200
        else:
            return jsonify({'message': 'Key no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ACTUALIZAR CRÉDITOS DE UNA KEY
@app.route('/creditos/<key>/<cantidad>', methods=['PUT'])
def actualizarCreditos(key, cantidad):
    try:
        cantidad = int(cantidad)
        result = keys_collection.find_one_and_update(
            {'valor': key},
            {'$set': {'creditos': cantidad}},
            return_document=True
        )
        if result:
            return jsonify({'message': f'Se actualizaron los créditos de la key {key} a: {cantidad}'}), 200
        else:
            return jsonify({'message': 'Key no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

 # RESTAR CRÉDITOS DE UNA KEY
@app.route('/restar_creditos/<key>/<cantidad>', methods=['PUT'])
def restarCreditos(key, cantidad):
    try:
        cantidad = int(cantidad)
        result = keys_collection.find_one_and_update(
            {'valor': key, 'creditos': {'$gte': cantidad}},  # Verifica que la cantidad de créditos sea mayor o igual a la cantidad a restar
            {'$inc': {'creditos': -cantidad}},  # Resta la cantidad de créditos especificada
            return_document=True
        )
        if result:
            return jsonify({'message': f'Se restaron {cantidad} créditos de la key {key}. Créditos restantes: {result["creditos"]}'}), 200
        else:
            return jsonify({'message': 'No hay suficientes créditos disponibles en la key o la key no fue encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
      
# VER TODAS LAS KEYS GENERADAS
@app.route('/keys', methods=['GET'])
def verKeys():
    try:
        keys = list(keys_collection.find({}, {"_id": 0}))  # Excluir el campo _id
        keys = json.loads(json.dumps(keys, default=str))  # Convertir ObjectId a cadena
        return jsonify({'keys': keys}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# BUSCAR KEY POR VALUE
@app.route('/key/<id>', methods=['GET'])
def busquedaKey(id):
    try:
        key = list(keys_collection.find({'valor': id}, {"_id": 0}))
        key = json.loads(json.dumps(key, default=str,indent=4))
        return jsonify({'key': key}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# @app.route('/buscar/<telefono>/<destino>', methods=['GET'])
# def buscar(telefono, destino):
#     try:
#         # Define los encabezados de autorización
#         headers = {
#             'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6IjM0NGNyeGFhbiJ9.Xvx8cP79AEVevZBfDSb9ApiTPn7TcjHmD3OxMbk5KQs'
#         }
        
#         # Construye la URL con los parámetros de búsqueda
#         url = f"http://161.132.39.14/v1/yp?k={telefono},{destino}"
        
#         # Realiza la solicitud POST a la API externa con los encabezados de autorización
#         response = requests.post(url, headers=headers)
        
#         print("Respuesta de la API externa:", response.text)
        
#         # Verificar el estado de la respuesta
#         if response.status_code == 200:
#             # Convertir la respuesta a formato JSON
#             data = response.json()
#             return jsonify(data), 200
#         else:
#             return jsonify({'error': 'Error en la consulta a la API externa'}), 500
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/consultar_numeros', methods=['POST'])
def consultar_numeros():
    try:
        # Extraer el DNI del cuerpo de la solicitud
        data = request.get_json()
        dni = data.get('dni')

        if not dni:
            return jsonify({'success': False, 'mensaje_error': 'El campo dni es requerido'}), 400

        # Definir el token de autorización
        token = 'Bearer eyJhdXRoIjoiSkxNIiwic3ViIjoiYWJjMTIzIiwiaWF0IjoxNTQ2Nzc5ODAwfQ.eyJ1c2VyIjoiam9obi5kb2UiLCJpYXQiOjE2MjQ0Nzg2Nzh9.bWl1Vwq7DFNhF3KvJ6KsT2dqWj5t4NsPl7Qe8Zm9Qyw'
        
        # URL de la segunda API
        url_segunda_api = 'http://45.136.19.181:3000/consultar_numeros'
        
        # Realiza la solicitud POST a la API externa
        response = requests.post(url_segunda_api, json={'dni': dni}, headers={'Authorization': token})

        if response.status_code == 200:
            data = response.json()

            # Extraer el nombre de la respuesta
            nombre = data.get('data', {}).get('nombre', '').strip()
            
            # Crear una respuesta con el nombre
            result = {
                'nombre': nombre
            }
            
            return jsonify(data), 200
        else:
            return jsonify({'success': False, 'mensaje_error': 'Error en la consulta a la API externa'}), 500

    except Exception as e:
        return jsonify({'success': False, 'mensaje_error': str(e)}), 500

@app.route('/telefono/<numero>', methods=['GET'])
def telefono(numero):
    try:
        # Define los encabezados de autorización
        headers = {
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6IjM0NGNyeGFhbiJ9.Xvx8cP79AEVevZBfDSb9ApiTPn7TcjHmD3OxMbk5KQs'
        }
        
        # Construye la URL con el parámetro DNI
        url = f"http://161.132.39.14/v1/tel?n={numero}"
        
        # Realiza la solicitud GET a la API externa con los encabezados de autorización
        response = requests.post(url, headers=headers)
        
        # Verificar el estado de la respuesta
        if response.status_code == 200:
            # Convertir la respuesta a formato JSON
            data = response.json()
            
            # Extraer el nombre y el apellido
            name = data.get('datos', {}).get('name', '').title()
            surname = data.get('datos', {}).get('surname', '').title()
            
            # Crear una nueva respuesta con solo el nombre y el apellido
            result = {
                'nombre': f"{name} {surname}"
            }
            
            return jsonify(result), 200
        else:
            return jsonify({'error': 'Error en la consulta a la API externa'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/qr/<codeqr>', methods=['POST'])
def qr(codeqr):
    try:
        # Define los encabezados de autorización
        headers = {
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6IjM0NGNyeGFhbiJ9.Xvx8cP79AEVevZBfDSb9ApiTPn7TcjHmD3OxMbk5KQs'
        }
        
        # Construye la URL con los parámetros de búsqueda
        url = f"http://161.132.39.14/v1/qr?qr={codeqr}"
        
        # Realiza la solicitud POST a la API externa con los encabezados de autorización
        response = requests.post(url, headers=headers)
        
        print("Respuesta de la API externa:", response.text)

        # Verificar el estado de la respuesta
        if response.status_code == 200:
            # Convertir la respuesta a formato JSON
            data = response.json()
            return jsonify(data), 200
        else:
            return jsonify({'error': 'Error en la consulta a la API externa'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

clientBilletera = MongoClient("mongodb+srv://allusers:TijO2LINkPVRIUeX@cluster0.gzb3q4e.mongodb.net/?retryWrites=true&w=majority", tlsAllowInvalidCertificates=True)
dbBilletera = clientBilletera.keys
data_collectionBilletera = dbBilletera.data  # Usamos la colección 'data' para almacenar los documentos

@app.route('/agregar_numero', methods=['POST'])
def agregar_documento():
    # Extraer datos del cuerpo de la solicitud
    data = request.get_json()
    numero = data.get('numero')
    nombre = data.get('nombre').title()
    destino = data.get('destino')
    user = data.get('user')

    # Obtener la IP del cliente real, extrayendo solo la primera IP si hay múltiples
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        # La primera IP en la lista es la IP del cliente
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.headers.get('X-Real-IP') or request.remote_addr

    # ip = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.remote_addr
    # ip = request.remote_addr
    # ip = data.get('ip')

    # Verificar que todos los campos están presentes
    if not all([numero, nombre, destino, user]):
        return jsonify({'success': False, 'mensaje_error': 'Faltan campos requeridos'}), 400
    
    # Verificar que el 'nombre' contenga al menos dos palabras
    if len(nombre.split()) < 2:
        return jsonify({'success': False, 'mensaje_error': 'El nombre debe contener al menos dos palabras'}), 400

    # Verificar que el 'numero' sea válido (exactamente 9 dígitos y comience con '9')
    if len(numero) != 9 or not numero.isdigit() or not numero.startswith('9'):
        return jsonify({'success': False, 'mensaje_error': 'El número debe contener exactamente 9 dígitos y comenzar con 9'}), 400

    # Buscar el documento en la colección
    existing_document = data_collectionBilletera.find_one({'numero': numero})

    if existing_document:
        # Verificar si el destino también coincide
        if existing_document.get('destino') == destino:
            return jsonify({'success': False, 'mensaje_error': 'El número y destino ya existen'}), 400

    # Crear el documento
    documento = {
        'numero': numero,
        'nombre': nombre,
        'destino': destino,
        'user': user,
        'ip': ip
    }

    # Insertar el documento en la colección
    result = data_collectionBilletera.insert_one(documento)
    
    return jsonify({'success': True, 'inserted_id': str(result.inserted_id)}), 201

@app.route('/buscar', methods=['GET'])
def buscar_documentos():
    
    numero = request.args.get('numero')

    if not numero:
        return jsonify({'success': False, 'mensaje_error': 'El campo numero es requerido'}), 400

    # Buscar todos los documentos por 'numero'
    documentos = list(data_collectionBilletera.find({'numero': numero}, {'_id': 0}))

    if documentos:
        return jsonify({'success': True, 'data': documentos, 'cantidad': len(documentos)}), 200
    else:
        return jsonify({'success': False, 'mensaje_error': 'Documentos no encontrados'}), 404

@app.route('/eliminar', methods=['DELETE'])
def eliminar_documento():
    try:
        # Extraer datos del cuerpo de la solicitud
        data = request.get_json()
        numero = data.get('numero')
        destino = data.get('destino')
        
        # Verificar que todos los campos están presentes
        if not all([numero, destino]):
            return jsonify({'success': False, 'mensaje_error': 'Faltan campos requeridos'}), 400

        # Buscar y eliminar el documento en la colección
        result = data_collectionBilletera.delete_one({'numero': numero, 'destino': destino})

        # Verificar si el documento fue eliminado
        if result.deleted_count == 0:
            return jsonify({'success': False, 'mensaje_error': 'No se encontró un documento con los datos proporcionados'}), 404
        
        return jsonify({'success': True, 'mensaje': 'Documento eliminado correctamente'}), 200
    except Exception as e:
        return jsonify({'success': False, 'mensaje_error': str(e)}), 500

@app.route('/eliminar_user', methods=['DELETE'])
def eliminar_documentos_por_usuario():
    try:
        # Extraer datos del cuerpo de la solicitud
        data = request.get_json()
        user = data.get('user')
        
        # Verificar que el campo 'user' está presente
        if not user:
            return jsonify({'success': False, 'mensaje_error': 'El campo user es requerido'}), 400

        # Buscar y eliminar todos los documentos que coincidan con el 'user'
        result = data_collectionBilletera.delete_many({'user': user})

        # Verificar si se eliminaron documentos
        if result.deleted_count == 0:
            return jsonify({'success': False, 'mensaje_error': 'No se encontraron documentos para el usuario proporcionado'}), 404
        
        return jsonify({'success': True, 'mensaje': f'Se eliminaron {result.deleted_count} documentos correctamente'}), 200
    except Exception as e:
        return jsonify({'success': False, 'mensaje_error': str(e)}), 500

@app.route('/buscar_user', methods=['GET'])
def consultar_documentos_por_usuario():
    try:
        # Extraer el parámetro 'user' de la consulta
        data = request.get_json()
        user = data.get('user')
        
        # Verificar que el campo 'user' está presente
        if not user:
            return jsonify({'success': False, 'mensaje_error': 'El campo user es requerido'}), 400

        # Buscar todos los documentos que coincidan con el 'user'
        documentos = list(data_collectionBilletera.find({'user': user}, {'_id': 0}))

        # Contar la cantidad de documentos
        cantidad = len(documentos)

        return jsonify({'success': True, 'cantidad': cantidad, 'documentos': documentos}), 200
    except Exception as e:
        return jsonify({'success': False, 'mensaje_error': str(e)}), 500

@app.route('/todos', methods=['GET'])
def ver_todos_documentos():
    try:
        # Obtener todos los documentos de la colección
        documentos = list(data_collectionBilletera.find({}, {'_id': 0}))
        
        if documentos:
            return jsonify({'success': True, 'data': documentos, 'cantidad': len(documentos)}), 200
        else:
            return jsonify({'success': False, 'mensaje_error': 'No se encontraron documentos'}), 404
    except Exception as e:
        return jsonify({'success': False, 'mensaje_error': 'Error al recuperar los documentos'}), 500


# def agregar_campo_autorizado():
#     try:
#         result = keys_collection.update_many(
#             {'autorizado': {'$exists': False}},  # Filtra los documentos que no tienen el campo 'autorizado'
#             {'$set': {'autorizado': True}}  # Establece el campo 'autorizado' en True para estos documentos
#         )
#         return f"Se agregó el campo 'autorizado' a {result.modified_count} claves."
#     except Exception as e:
#         return str(e)
# # Llama a esta función para agregar el campo 'autorizado' a las claves existentes
# resultado = agregar_campo_autorizado()
# print(resultado)
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=80)



#USAR PARA INSTALAR LAS LIBRERIAS NECESARIAS 
#pip install -r requirements.txt
