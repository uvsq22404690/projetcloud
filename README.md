# ProjetCloud – Générateur OCI & Déploiement Kubernetes

Projet académique – Infrastructure as Code  

Une application permettant de **générer automatiquement une image OCI (Docker) et des manifests Kubernetes à partir d’un profil YAML**, puis de déployer l’application sur un cluster Kubernetes.

---

## Description du projet

Ce projet met en œuvre une approche **Infrastructure as Code (IaC)** basée sur un fichier profil YAML.

À partir d’un simple fichier de configuration, le générateur permet de :

- Lire un profil d’application (YAML)
- Générer automatiquement un `Dockerfile`
- Construire une image OCI (Docker)
- Publier l’image sur un registry public (DockerHub)
- Générer les manifests Kubernetes :
  - Namespace
  - Deployment
  - Service
- Générer des **NetworkPolicies sécurisées** :
  - Default Deny Ingress
  - Règles d’accès autorisées

---

## Structure du projet

projetcloud/

│

├── profiles/ # Profils YAML des applications

│ └── web-debian.yaml

│

├── generator/ # Code Python du générateur

│ └── generate.py

│

├── dist/ # Résultats générés automatiquement

│ └── web-debian/

│ ├── Dockerfile

│ └── k8s.yaml

│

├── scripts/ # Scripts d'automatisation (optionnel)

├── templates/ # Templates (optionnel)

└── README.md

---

## Prérequis

### Outils obligatoires

- Git

- Docker Desktop

- Python 3.10+

- pip

- kubectl

- kind (ou minikube)

---

### Dépendances Python

Installer PyYAML :



```bash
pip install pyyaml
```
---

## Profil d'entrée (YAML)



Exemple : `profiles/web-debian.yaml`



```yaml
id: web-debian

os:

&nbsp; distro: debian

&nbsp; version: "12"

packages:

&nbsp; - nginx

&nbsp; - curl

&nbsp; - wget

app:

&nbsp; containerPort: 80

network:

&nbsp; defaultDenyIngress: true

&nbsp; allowIngress:

&nbsp;   - from: ingress-controller

&nbsp;     protocol: TCP

&nbsp;     port: 80
```

---

## Génération des fichiers (Dockerfile + Kubernetes YAML)

Exécuter :

```bash
python generator/generate.py profiles/web-debian.yaml readnamane
```

Build et Push de l'image Docker :

- Build
```bash
docker build -t readnamane/web-debian:<TAG> -f dist/web-debian/Dockerfile .
```

- Push
```bash
docker push readnamane/web-debian:<TAG>
```
---

## Déploiement Kubernetes avec kind

### Créer un cluster kind 

```bash
kind create cluster --name projet
```

Vérifier le cluster:
```bash
kubectl get nodes
```
---

Déployer l'application:
```bash
kubectl apply -f dist/web-debian/k8s.yaml
```
---

Vérifier les ressources:
```bash
kubectl get all -n web-debian-ns

kubectl get networkpolicy -n web-debian-ns
```
---

Le Service est de type ClusterIP, donc on utilise un port-forward :
```bash
kubectl -n web-debian-ns port-forward service/web-debian 8080:80
```
---

Puis accéder via navigateur :

http://localhost:8080

La page nginx "Welcome to nginx!" confirme que le déploiement est fonctionnel.

---

Sécurité réseau (NetworkPolicies):

Le fichier k8s.yaml inclut :

Une NetworkPolicy default-deny-ingress (tout bloquer en entrée)

Une NetworkPolicy allow-from-ingress (autoriser uniquement TCP/80 depuis l’ingress controller)

---

## Vérifications / Debug

### Vérifier l'état des pods
```bash
kubectl get pods -n web-debian-ns
```

Vérifier le service:

```bash
kubectl get svc -n web-debian-ns
```

Vérifier les NetworkPolicies:

```bash
kubectl get networkpolicy -n web-debian-ns
```

Vérifier les logs Nginx:

```bash
kubectl logs -n web-debian-ns -l app=web-debian
```

Décrire le pod en cas d'erreur:

```bash
kubectl describe pod -n web-debian-ns -l app=web-debian
```


