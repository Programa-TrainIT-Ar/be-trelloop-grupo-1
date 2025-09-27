# Proyecto Trello Clone Grupo 1:
Sigue estos pasos para preparar el proyecto en tu entorno local:

1. Inicializar una carpera en blanco, en ella:
   
git clone https://github.com/Programa-TrainIT-Ar/be-trelloop-grupo-1 .

2. Crear un entorno virtual:
   
conda create -n trello-clone-grupo-1 python=3.10

3. Activar el entorno virtual:
   
conda activate trello-clone-grupo-1

4. Instalar dependencias:
   
pip install pipenv

pipenv install

5. Ejecutar migraciones:
   
export FLASK_APP=app:create_app

flask db init

flask db migrate

flask db upgrade

6. Levantar servidor:
python -m app.main
