Param(
  [Parameter(Mandatory=$true)]
  [string]$Profile,

  [Parameter(Mandatory=$true)]
  [string]$DockerUser
)

$ErrorActionPreference = "Stop"

function Require-Cmd($cmd) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    throw "Commande manquante: $cmd"
  }
}

Require-Cmd git
Require-Cmd docker
Require-Cmd python
Require-Cmd kubectl

Write-Host "[1/4] Génération depuis le profil: $Profile"
python .\generator\generate.py $Profile $DockerUser

# Récupérer l'image tag depuis la sortie générée (on relit le k8s.yaml)
# On déduit l'appId depuis le chemin du profil: profiles/<id>.yaml
$appId = [System.IO.Path]::GetFileNameWithoutExtension($Profile)
$k8sFile = ".\dist\$appId\k8s.yaml"
if (-not (Test-Path $k8sFile)) { throw "Fichier introuvable: $k8sFile" }

$imageLine = Select-String -Path $k8sFile -Pattern "image:\s*" | Select-Object -First 1
if (-not $imageLine) { throw "Impossible de trouver la ligne image: dans $k8sFile" }

$image = ($imageLine.Line -replace "^\s*image:\s*", "").Trim()
if (-not $image) { throw "Tag image vide" }

Write-Host "[2/4] Build image: $image"
docker build -t $image -f ".\dist\$appId\Dockerfile" .

Write-Host "[3/4] Push image: $image"
docker push $image

Write-Host "[4/4] Déploiement Kubernetes: $k8sFile"
kubectl apply -f $k8sFile

Write-Host ""
Write-Host "OK ✅"
Write-Host "Image: $image"
Write-Host "Namespace: $($appId)-ns"
Write-Host "Tester:"
Write-Host "  kubectl -n $($appId)-ns port-forward service/$appId 8080:80"
