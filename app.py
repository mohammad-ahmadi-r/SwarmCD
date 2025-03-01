from flask import Flask, render_template, request, redirect, url_for, abort, jsonify
import sqlite3
import subprocess
import docker
import logging
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

SECRET_TOKEN = os.getenv("SECRET_TOKEN")
GIT_USERNAME = os.getenv("GIT_USERNAME")
GIT_PASSWORD = os.getenv("GIT_PASSWORD")
BROWSER_TOKEN = os.getenv("BROWSER_TOKEN")
ROOT_PATH = os.getenv("ROOT_PATH")


app = Flask(__name__)
logger = logging.getLogger(__name__)

DATABASE = 'app.db'

def init_db():
    logger.info("Initializing the database")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            service_image TEXT NOT NULL,
            image_tag TEXT NOT NULL,
            image_name TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_services():
    logger.info("Loading services and their images.")
    docker_client = docker.from_env()
    try:
        services = docker_client.services.list()
        services_list = []
        for service in services:
            service_name = service.name
            service_image = service.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image']
            image_tag = service_image.split(':')[-1] 
            image_name = service_image.split(':')[0]
            services_list.append((service_name, service_image, image_tag))

        logger.info("Services loaded successfully.")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        for service_name, service_image, image_tag in services_list:
            cursor.execute("INSERT INTO services (service_name, service_image, image_tag, image_name) VALUES (?, ?, ?, ?)", (service_name, service_image, image_tag, image_name))
        conn.commit()
        conn.close()
        logger.info("Services stored successfully.")
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")


def get_service_by_image(image_name):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT service_name FROM services WHERE service_image = ?", (image_name,))
        result = cursor.fetchall()
        return result

@app.route(f"{ROOT_PATH}/reload", methods=["GET"])
def get_services_reload():
    token = request.args.get("token")
    if not token:
        return render_template("401.html"), 401

    if token != BROWSER_TOKEN:
        return render_template("401.html"), 403
    try:
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM services')
        conn.commit()
        conn.close()
        get_services()
        return redirect(url_for('home', token=BROWSER_TOKEN))
    except Exception as e:
        logger.error(f"Error occurred while reloading services: {e}")
        return {"image": "Error occurred"}, 500



@app.route(f"{ROOT_PATH}/", methods=["POST"])
def gitlab_webhook():
    try:
        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1]
        if token != SECRET_TOKEN:
            return "Invalid secret token", 403

        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Invalid Authorization header format"}), 401

        payload = request.get_json()
        if not payload:
            return "No JSON payload received", 400

        url = payload.get("project").get("image_name")
        tag = payload.get("project").get("tag_name")
        image_name = f"{url}:{tag}"
        if not image_name:
            return {"error": "Image name not found in the webhook payload"}, 400

        auth_config = {
            'username': GIT_USERNAME,
            'password': GIT_PASSWORD
        }
        client = docker.from_env()


        service_name = get_service_by_image(image_name)
        if not service_name:
            return {"error": f"Service name not found in the swarm cluster {image_name}"}, 400
        expired_service = client.services.get(service_name[0][0])

        if expired_service:
            new_image = client.images.pull(image_name, auth_config=auth_config)
            expired_service.update(image=image_name,force_update=True)
            return {"message": f"Service updated successfully: {image_name, expired_service}"}, 200
        else:
            return {"image": image_name, "services": [], "message": "No services found for the given image"}, 200

    except Exception as e:
        return {"error": str(e), "data":new_image}, 500

@app.route(f"{ROOT_PATH}/")
def home():
    token = request.args.get("token")
    if not token:
        return render_template("401.html"), 401

    if token != BROWSER_TOKEN:
        return render_template("401.html"), 403

    reload_url = url_for('get_services_reload', token=token)
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute('SELECT service_name, service_image, image_tag, image_name FROM services ORDER BY service_name ASC')
    services = cursor.fetchall()
    conn.close()
    return render_template('index.html', services=services, token=token, reload_url=reload_url)

if __name__ == "__main__":
    logger.info("Welcome to SwarmCD")
    init_db()
    get_services()
    app.run(host="0.0.0.0", port=5000)