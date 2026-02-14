import sys
import yaml
import hashlib
from pathlib import Path


def die(msg: str, code: int = 1):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def load_profile(path: Path) -> dict:
    if not path.exists():
        die(f"Profile not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        die("Profile must be a YAML mapping/object.")
    return data


def required(d: dict, key: str):
    if key not in d:
        die(f"Missing required field: {key}")
    return d[key]


def slug_hash(profile: dict) -> str:
    raw = yaml.safe_dump(profile, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:8]


def make_dockerfile(profile: dict) -> str:
    os_cfg = required(profile, "os")
    distro = required(os_cfg, "distro")
    version = required(os_cfg, "version")

    pkgs = profile.get("packages", [])
    if not isinstance(pkgs, list):
        die("packages must be a list")
    pkgs_str = " ".join(pkgs)

    app = profile.get("app", {})
    container_port = int(app.get("containerPort", 80))

    if distro.lower() != "debian":
        die("For now, this generator supports only debian in os.distro")

    base = f"debian:{version}"

    lines = [
        f"FROM {base}",
        "RUN apt-get update \\",
        f"    && apt-get install -y --no-install-recommends {pkgs_str} \\",
        "    && rm -rf /var/lib/apt/lists/*",
        "",
        f"EXPOSE {container_port}",
        "",
        'CMD ["nginx", "-g", "daemon off;"]',
        "",
    ]
    return "\n".join(lines)


def make_k8s_yaml(profile: dict, image: str) -> str:
    app_id = required(profile, "id")

    app = profile.get("app", {})
    container_port = int(app.get("containerPort", 80))

    name = app_id.replace("_", "-").lower()
    ns = f"{name}-ns"

    net = profile.get("network", {})
    default_deny = bool(net.get("defaultDenyIngress", True))

    allow = net.get("allowIngress", [])
    if not isinstance(allow, list):
        die("network.allowIngress must be a list")

    allow_ports = []
    for rule in allow:
        if not isinstance(rule, dict):
            continue
        proto = (rule.get("protocol") or "TCP").upper()
        port = int(rule.get("port", 80))
        allow_ports.append((proto, port))

    if not allow_ports:
        allow_ports = [("TCP", 80)]

    allow_ports_yaml = "\n".join(
        [f"      - protocol: {p}\n        port: {pt}" for (p, pt) in allow_ports]
    )

    deny_policy = ""
    if default_deny:
        deny_policy = f"""---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {name}-default-deny-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels:
      app: {name}
  policyTypes:
    - Ingress
"""

    allow_policy = f"""---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {name}-allow-from-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels:
      app: {name}
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: ingress-nginx
          podSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
{allow_ports_yaml}
"""

    k8s = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {ns}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
        - name: {name}
          image: {image}
          ports:
            - containerPort: {container_port}
---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {ns}
spec:
  selector:
    app: {name}
  ports:
    - name: http
      port: 80
      targetPort: {container_port}
  type: ClusterIP
{deny_policy}{allow_policy}
"""
    return k8s


def main():
    if len(sys.argv) != 3:
        print("Usage: python generator/generate.py <profile.yaml> <dockerhub_user>", file=sys.stderr)
        sys.exit(2)

    profile_path = Path(sys.argv[1])
    dockerhub_user = sys.argv[2].strip()

    if not dockerhub_user:
        die("dockerhub_user is required")

    profile = load_profile(profile_path)
    app_id = required(profile, "id")
    h = slug_hash(profile)

    image = f"{dockerhub_user}/{app_id}:{h}"

    out_dir = Path("dist") / app_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "Dockerfile").write_text(make_dockerfile(profile), encoding="utf-8")
    (out_dir / "k8s.yaml").write_text(make_k8s_yaml(profile, image), encoding="utf-8")

    print("Generated:")
    print(f" - {out_dir / 'Dockerfile'}")
    print(f" - {out_dir / 'k8s.yaml'}")
    print("")
    print("Image tag:")
    print(f" - {image}")
    print("")
    print("Next commands:")
    print(f"  docker build -t {image} -f {out_dir / 'Dockerfile'} .")
    print(f"  docker push {image}")
    print(f"  kubectl apply -f {out_dir / 'k8s.yaml'}")


if __name__ == "__main__":
    main()
