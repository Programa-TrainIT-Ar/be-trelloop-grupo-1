# Proyecto Trello Clone Grupo 1:
Sigue estos pasos para preparar el proyecto en tu entorno local:

1. Inicializar una carpera en blanco, en ella:
2. 
git clone https://github.com/Programa-TrainIT-Ar/be-trelloop-grupo-1 .

3. Crear un entorno virtual:
4. 
conda create -n trello-clone-grupo-1 python=3.10

5. Activar el entorno virtual:
6. 
conda activate trello-clone-grupo-1

7. Instalar dependencias:
8. 
pip install pipenv

pipenv install

6. Ejecutar migraciones:
7. 
export FLASK_APP=app:create_app

flask db init

flask db migrate

flask db upgrade

8. Levantar servidor:
python -m app.main
