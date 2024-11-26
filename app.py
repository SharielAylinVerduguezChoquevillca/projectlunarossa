from flask import Flask, render_template, jsonify, send_from_directory, request, redirect, session, url_for
from flask_cors import CORS
from extensions import db, migrate
from controllers.category_controller import category_blueprint
from controllers.product_controller import product_blueprint
from controllers.user_controller import user_blueprint
from controllers.cart_controller import cart_blueprint  
from services.carrito_service import CarritoService  
from services.product_service import ProductService  
from models.product import Producto
from models.category import Category
from models.user import User
from models.cart import Carrito




import os


app = Flask(__name__, static_url_path='/static')
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.secret_key ='1234'



app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


app.config['UPLOAD_FOLDER'] = os.path.join('static', 'imagenes')
app.static_folder = 'static'

# Asociar la base de datos con la app
db.init_app(app)
migrate.init_app(app, db)

# Registrar Blueprints
app.register_blueprint(category_blueprint, url_prefix='/api')
app.register_blueprint(product_blueprint, url_prefix='/api')
app.register_blueprint(user_blueprint, url_prefix='/api')
app.register_blueprint(cart_blueprint, url_prefix='/api')  # Registra el blueprint del carrito

# Crear las tablas en la base de datos
with app.app_context():
    db.create_all()

def update_image_urls():
    with app.app_context():
        productos = Producto.query.all()
        for producto in productos:
            if producto.imagen_url:
                if not producto.imagen_url.startswith('/static/'):
                    if producto.imagen_url.startswith('imagenes/'):
                        producto.imagen_url = f"/static/{producto.imagen_url}"
                    else:
                        producto.imagen_url = f"/static/imagenes/{producto.imagen_url}"
        db.session.commit()
    print("URLs de imágenes actualizadas.")

# Rutas para servir archivos estáticos
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Rutas para la interfaz de usuario
@app.route('/')
@app.route('/index')
def lista_productos():
    productos = ProductService.get_all_products()
    categorias = Category.query.all()
    username = session.get('username')  # Obtener el nombre del usuario logueado
    return render_template('index.html', productos=productos, categorias=categorias, username=username)

@app.before_request
def check_logged_in():
    if 'user_id' not in session:
        if request.endpoint not in ['login', 'static']:  # Excluye login y rutas estáticas
            return redirect(url_for('login'))



# Supongamos que tienes un modelo `User` para verificar las credenciales.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verifica si el usuario existe y la contraseña es correcta.
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            # Inicia la sesión.
            session['user_id'] = user.id

            # Redirige a la página de categorías.
            return redirect(url_for('categorias'))
        else:
            # Puedes agregar un mensaje para manejar errores aquí si lo deseas.
            return render_template('login.html', error="Usuario o contraseña incorrectos")

    return render_template('login.html')


@app.route('/crear_producto', methods=['GET'])
def crear_producto_form():
    categorias = Category.query.all()
    return render_template('crear_producto.html', categorias=categorias)

@app.route('/producto/<int:id>')
def producto_detalle(id):
    producto = ProductService.get_product_by_id(id)  # Usamos el servicio para obtener el producto
    return render_template('producto_detalle.html', producto=producto)

@app.route('/producto/editar/<int:id>', methods=['GET'])
def editar_producto_form(id):
    producto = ProductService.get_product_by_id(id)  # Usamos el servicio para obtener el producto
    categorias = Category.query.all()
    return render_template('editar_producto.html', producto=producto, categorias=categorias)

@app.route('/producto/editar/<int:id>', methods=['POST'])
def editar_producto(id):
    # Actualizamos los datos del producto usando el servicio
    ProductService.update_product(id, request.form, request.files)
    return redirect(url_for('producto_detalle', id=id))

@app.route('/categoria/<int:id>')
def categoria_productos(id):
    # Lógica para obtener los productos de la categoría con el id proporcionado
    return render_template('categoria_productos.html', id=id)

@app.route('/categorias')
def categorias():
    # Verifica si el usuario está autenticado.
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    productos = ProductService.get_all_products()  # Obtén los productos
    categorias = Category.query.all()  # Obtén las categorías
    return render_template('categoria.html', productos=productos, categorias=categorias)




# Rutas API para manejar el carrito
@app.route('/api/carrito/<int:id>', methods=['GET'])
def get_cart(id):
    carrito = CarritoService.get_carrito_by_id(id)  # Usamos el servicio de carrito
    if carrito:
        productos = carrito.get_productos()  # Accede a los productos asociados
        return jsonify([producto.to_dict() for producto in productos])
    else:
        return jsonify({'message': 'Carrito no encontrado'}), 404

@app.route('/user/create_account')
def create_account():
    return render_template('create_account.html')  # Este es el HTML para la creación de cuentas


@app.route('/api/carrito/<int:id>/comprar', methods=['DELETE'])
def comprar_carrito(id):
    try:
        # Llama al servicio para completar la compra y eliminar los productos o el carrito
        CarritoService.complete_purchase_and_delete_all(id)
        return jsonify({'message': 'Compra realizada y carrito eliminado exitosamente'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        # Obtener datos del cuerpo de la solicitud
        data = request.get_json()

        # Verificar que se envíen todos los campos necesarios
        if not all(key in data for key in ('username', 'email', 'password', 'rol')):
            return jsonify({'message': 'Faltan datos necesarios (username, email, password, rol)'}), 400

        # Crear una nueva instancia de User
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],  # Considera encriptar la contraseña antes de almacenarla
            rol=data['rol']
        )

        # Guardar el nuevo usuario en la base de datos
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'Usuario creado con éxito', 'user': new_user.to_dict()}), 201
    except Exception as e:
        return jsonify({'message': 'Error al crear el usuario', 'error': str(e)}), 500


@app.route('/delete_product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    try:
        # Buscar el producto por su ID
        product = Producto.query.get(product_id)
        if not product:
            return jsonify({'message': 'Producto no encontrado'}), 404

        # Eliminar el producto de la base de datos
        db.session.delete(product)
        db.session.commit()

        return jsonify({'message': f'Producto con ID {product_id} eliminado con éxito'}), 200
    except Exception as e:
        return jsonify({'message': 'Error al eliminar el producto', 'error': str(e)}), 500

@app.route('/delete_category/<int:id>', methods=['DELETE'])
def delete_category(id):
    try:
        # Buscar la categoría por ID
        categoria = Category.query.get(id)
        if not categoria:
            return jsonify({'message': 'Categoría no encontrada'}), 404

        # Eliminar la categoría de la base de datos
        db.session.delete(categoria)
        db.session.commit()

        return jsonify({'message': f'Categoría con ID {id} eliminada con éxito'})

    except Exception as e:
        db.session.rollback()  # En caso de error, revertir los cambios
        return jsonify({'message': 'Error al eliminar la categoría', 'error': str(e)}), 500




@app.route('/api/categorias/<int:id>', methods=['PUT'])
def actualizar_categoria(id):
    # Buscar la categoría por ID
    categoria = Category.query.get_or_404(id)
    
    # Obtener el nuevo nombre de la categoría desde el cuerpo de la solicitud
    nuevo_nombre = request.json.get('name')
    
    if not nuevo_nombre:
        return jsonify({'error': 'El nombre de la categoría es obligatorio'}), 400

    try:
        # Actualizar el nombre de la categoría
        categoria.name = nuevo_nombre
        db.session.commit()  # Guardar los cambios en la base de datos
        
        return jsonify({'message': 'Categoría actualizada con éxito', 'categoria': categoria.to_dict()}), 200
    except Exception as e:
        db.session.rollback()  # Rollback en caso de error
        return jsonify({'error': 'Error al actualizar la categoría', 'details': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        update_image_urls()  # Actualizar URLs de imágenes al iniciar la aplicación
    app.run(debug=True)
    
