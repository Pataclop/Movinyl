# Movinyl - Containerized Version

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Multi-Platform](https://img.shields.io/badge/Platforms-Linux%20%7C%20macOS%20%7C%20Windows-green.svg)](https://hub.docker.com/)

Movinyl est maintenant disponible en version conteneurisée, permettant une installation et utilisation faciles sur Linux, macOS et Windows sans configuration complexe du système.

## 🚀 Démarrage Rapide

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) installé et fonctionnel
- [Docker Compose](https://docs.docker.com/compose/install/) (optionnel, pour une utilisation avancée)

### Installation

1. **Clonez le repository :**
   ```bash
   git clone https://github.com/Pataclop/Movinyl.git
   cd Movinyl
   ```

2. **Construisez l'image Docker :**
   ```bash
   ./run.sh build
   ```

## 📋 Utilisation

### Méthode Simple (Recommandée)

Utilisez le script `run.sh` qui détecte automatiquement votre OS et lance Movinyl dans un conteneur :

```bash
# Construire l'image
./run.sh build

# Générer des disques à partir de vidéos
./run.sh disk

# Générer des pages à partir des disques
./run.sh page

# Démarrer un shell interactif dans le conteneur
./run.sh shell
```

### Méthode Docker Compose

Pour une utilisation plus avancée avec Docker Compose :

```bash
# Construire et lancer
docker-compose up --build

# Ou en arrière-plan
docker-compose up -d --build
```

### Méthode Docker Direct

```bash
# Générer des disques
docker run --rm -it -v "$(pwd)/PROCESSING_ZONE:/app/PROCESSING_ZONE" movinyl disk

# Générer des pages
docker run --rm -it -v "$(pwd)/PAGE_ZONE:/app/PAGE_ZONE" movinyl page
```

## 📁 Structure des Répertoires

```
Movinyl/
├── PROCESSING_ZONE/     # Placez vos vidéos ici
├── PAGE_ZONE/          # Les disques générés iront ici pour créer des pages
├── run.sh             # Script de lancement multi-plateforme
├── docker-compose.yml # Configuration Docker Compose
├── Dockerfile         # Définition de l'image Docker
└── ...               # Autres fichiers du projet
```

## 🔄 Workflow Complet

### 1. Préparation

Placez vos fichiers vidéo dans le dossier `PROCESSING_ZONE` :
- Formats supportés : MP4, MKV, AVI, MOV, FLV, WMV, WebM, MPG, MPEG, 3GP, OGV, MTS, M2TS, TS
- Le nom du fichier doit correspondre au format : `Titre_Année.ext` (ex: `Inception_2010.mp4`)

### 2. Génération des Disques

```bash
./run.sh disk
```

Cette commande :
- Analyse chaque vidéo dans `PROCESSING_ZONE`
- Extrait 2000 frames équidistantes
- Génère une visualisation en forme de disque vinyle
- Produit des fichiers PNG nommés d'après les vidéos

### 3. Génération des Pages

Déplacez les fichiers PNG générés vers `PAGE_ZONE`, puis :

```bash
./run.sh page
```

Cette commande :
- Récupère les informations du film via TMDB
- Génère des pages avec titre, réalisateur, durée, etc.
- Produit les visualisations finales

## 🖥️ Support Multi-Plateforme

### Linux

```bash
# Installation de Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Utilisation
./run.sh build
./run.sh disk
```

### macOS

```bash
# Installation de Docker Desktop
# Téléchargez depuis : https://www.docker.com/products/docker-desktop

# Utilisation
./run.sh build
./run.sh disk
```

### Windows

#### Avec PowerShell :
```powershell
# Installation de Docker Desktop
# Téléchargez depuis : https://www.docker.com/products/docker-desktop

# Dans PowerShell :
.\run.sh build
.\run.sh disk
```

#### Avec Command Prompt :
```cmd
# Installation de Docker Desktop
# Téléchargez depuis : https://www.docker.com/products/docker-desktop

# Dans CMD :
run.sh build
run.sh disk
```

## ⚙️ Configuration Avancée

### Variables d'Environnement

- `MOVINYL_FRAME_COUNT` : Nombre de frames à extraire (défaut: 2000)
- `MOVIES_DIR` : Répertoire externe contenant des vidéos (pour Docker Compose)

### Personnalisation Docker Compose

Modifiez `docker-compose.yml` pour :
- Monter des volumes supplémentaires
- Configurer des variables d'environnement
- Ajuster les limites de ressources

```yaml
services:
  movinyl:
    environment:
      - MOVINYL_FRAME_COUNT=1500
    volumes:
      - ./my_movies:/app/videos:ro
      - ./output:/app/output:rw
```

## 🐛 Dépannage

### Problèmes Courants

**Erreur "Docker not found"**
- Vérifiez que Docker est installé et démarré
- Sur Linux : `sudo systemctl start docker`
- Sur macOS/Windows : Lancez Docker Desktop

**Erreur "No videos found"**
- Vérifiez que vos vidéos sont dans `PROCESSING_ZONE`
- Assurez-vous que les permissions des fichiers sont correctes

**Erreur "Build failed"**
- Vérifiez votre connexion internet (pour les dépendances)
- Essayez : `docker system prune -a` puis rebuild

**Performance lente**
- Sur Windows/WSL : Activez WSL2
- Augmentez la RAM allouée à Docker (4GB minimum recommandé)

### Logs et Debug

```bash
# Voir les logs du conteneur
docker logs <container_id>

# Démarrer un shell pour debug
./run.sh shell

# Vérifier l'état de Docker
docker system info
```

## 🔧 Développement

Pour contribuer au projet conteneurisé :

1. Modifiez les fichiers source
2. Testez avec : `./run.sh build && ./run.sh disk`
3. Soumettez une Pull Request

### Structure du Conteneur

- **Base** : Ubuntu 22.04
- **Langages** : Python 3.10, C++ (GCC)
- **Bibliothèques** : OpenCV, FFmpeg, ImageMagick, TMDB API
- **Outils** : bc, pkg-config, build-essential

## 📄 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

## 📞 Support

- 🐛 [Issues GitHub](https://github.com/Pataclop/Movinyl/issues)
- 💬 [Discussions](https://github.com/Pataclop/Movinyl/discussions)
- 📧 project.movinyl@gmail.com

---

*Transformez vos films préférés en œuvres d'art visuelles ! 🎬🎨*
