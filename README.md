# SwarmCD - Continuous Deployment App

SwarmCD is a lightweight Flask application that provides webhook-based automated deployments for Docker Swarm clusters. It enables seamless updates to your services when a new image is built.

## Features
- Simple and lightweight Flask application with SQLite3
- Fully containerized using Docker
- Easily deployable using `docker stack deploy`
- Webhook support for automated service updates
- Nginx integration for secure external access

## Prerequisites
- Docker installed on your machine
- An active Docker Swarm cluster

## Getting Started

### 1. Create a Deployment Directory
Ensure your Swarm cluster is running. Then, create a directory (e.g., `SwarmCD`).

### 2. Create `docker-compose.yml`
```yaml
version: '3.8'

services:
  flask:
    image: dockerhub.com/swarmcd:0.1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "5000:5000"
    networks:
      - swarmcd-network

networks:
  swarmcd-network:
    driver: overlay
```

### 3. Create `.env` File
```sh
SECRET_TOKEN=ZY95q3443KvPsil  # Custom authentication token for webhook requests
GIT_USERNAME=username        # Docker registry username
GIT_PASSWORD=password        # Docker registry password
BROWSER_TOKEN=123456         # Custom Token for web interface access
ROOT_PATH=/hook              # Custom path for webhooks
```

### 4. Deploy the Application
Run the following command to deploy the stack:
```sh
docker stack deploy -c docker-compose.yml swarmcd
```

## Accessing the Web Interface
Once deployed, access the web UI to view services and images:
```
http://<swarmcd-deployed-machine-ip>:5000/hook/?token=BROWSER_TOKEN
```
This interface displays all services in the cluster along with their image tags. 
It also allows you to reload the service list, which is essential when new services are added or removed.

Now Swarmcd is all set to use. lets use it



## Webhook Functionality
### Environment Variables Setup

```sh
export SECRET_TOKEN=ZY95q3443KvPsil
export ROOT_PATH=/hook
```

### Triggering a Deployment
To update a service with a new image, send a POST request to the webhook:
```sh
curl -X POST "http://<swarmcd-deployed-machine-ip>:5000$ROOT_PATH/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $SECRET_TOKEN" \
    -d '{
        "project": {
            "image_name": "git.mygit.com/myapp",
            "tag_name": "latest"
        }
    }'
```

## Integrating with GitLab CI
Define `SECRET_TOKEN` in your GitLab CI/CD runner variables and integrate the webhook in `.gitlab-ci.yml`:

```yaml
stages:
  - build
  - deploy

variables:
  DOCKER_REGISTRY: "git.mygit.com:5050"
  IMAGE_NAME: "$DOCKER_REGISTRY/myapp"
  IMAGE_TAG: "latest"
  ROOT_PATH: "/hook"

before_script:
  - docker login -u "$CI_REGISTRY_USER" -p "$CI_REGISTRY_PASSWORD" "$CI_REGISTRY"

build_app:
  stage: build
  script:
    - docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
    - docker push "$IMAGE_NAME:$IMAGE_TAG"
  only:
    - main

deploy_service:
  stage: deploy
  script:
    - curl -X POST "http://<swarmcd-deployed-machine-ip>:5000$ROOT_PATH/" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $SECRET_TOKEN" \
        -d '{"project":{"image_name":"$IMAGE_NAME","tag_name":"$IMAGE_TAG"}}'
```
Now we have a fully automated CICD for swarm cluster.

## Using Nginx as a Proxy
To expose the webhook securely, add the following configuration to your Nginx `server` block:

```nginx
location /hook/ {
    proxy_pass http://<swarmcd-deployed-machine-ip>:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### Accessing via Nginx
```
https://project.com/hook/?token=BROWSER_TOKEN
```

### Webhook Usage via Nginx
```sh
curl -X POST "https://project.com/hook/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $SECRET_TOKEN" \
    -d '{
        "project": {
            "image_name": "git.mygit.com/myapp",
            "tag_name": "latest"
        }
    }'
```

Note that this may not work very well for multi node swarm cluster
## Contributing
I welcome contributions! Feel free to fork this repository and submit pull requests.

