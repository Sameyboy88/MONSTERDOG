"""
FLASK + DASH NFT INTERFACE — MONSTERDOG TOTALITY EDITION v2
=========================================================
• Real IPFS pin via `ipfshttpclient` (or Pinata JWT fallback)
• Signed ERC‑721 mint via `web3.py`
• Fractal QR generation
• Embedded Dash *Vortex* viewer (Plotly 3‑D)
• Dockerfile & docker‑compose specs included below

Install dependencies (`pip install -r requirements.txt`):
    flask qrcode pillow ipfshttpclient web3 dash plotly
Set the environment variables listed below before launch.
"""
from __future__ import annotations
import io, json, os, tempfile, datetime as dt
from pathlib import Path

import qrcode
from flask import Flask, request, send_file, url_for

# 3rd‑party runtime deps (heavy — import lazily where possible)
import ipfshttpclient  # communicates with local IPFS daemon
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

# ── Dash (Vortex visual) ───────────────────────────────────────────
import dash
from dash import html, dcc
import plotly.graph_objects as go

###############################################################################
# 0. CONFIGURATION ────────────────────────────────────────────────────────────
###############################################################################
UPLOAD_DIR = Path(tempfile.gettempdir()) / "monsterdog_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ENV (secrets / infra)
IPFS_API               = os.getenv("IPFS_API", "/ip4/127.0.0.1/tcp/5001")
PINATA_JWT             = os.getenv("PINATA_JWT")
WEB3_URI               = os.getenv("WEB3_PROVIDER_URI", "https://rpc.ankr.com/eth")
CONTRACT_ADDRESS       = os.getenv("CONTRACT_ADDRESS", "0xYourContract")
CONTRACT_ABI_JSON      = os.getenv("CONTRACT_ABI_JSON", "[]")  # stringified ABI
WALLET_PRIVATE_KEY     = os.getenv("WALLET_PRIVATE_KEY", "")
WALLET_ADDRESS         = os.getenv("WALLET_PUBLIC_ADDRESS", "0xYourWallet")

###############################################################################
# 1. HELPERS ──────────────────────────────────────────────────────────────────
###############################################################################

def upload_to_ipfs(path: Path) -> str:
    """Pin via local IPFS daemon or Pinata JWT."""
    if PINATA_JWT:
        import requests
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        with path.open("rb") as fp:
            files = {"file": fp}
            headers = {"Authorization": f"Bearer {PINATA_JWT}"}
            r = requests.post(url, files=files, headers=headers, timeout=120)
        r.raise_for_status()
        cid = r.json()["IpfsHash"]
    else:
        with ipfshttpclient.connect(IPFS_API) as cli:
            cid = cli.add(str(path))["Hash"]
    return f"ipfs://{cid}"


def mint_nft(token_uri: str) -> str:
    """Send `createNFT(tokenURI)` TX → returns TX hash."""
    if not WALLET_PRIVATE_KEY:
        raise RuntimeError("WALLET_PRIVATE_KEY absent – set env var")

    w3 = Web3(HTTPProvider(WEB3_URI))
    if "poa" in WEB3_URI:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    contract = w3.eth.contract(address=Web3.toChecksumAddress(CONTRACT_ADDRESS),
                               abi=json.loads(CONTRACT_ABI_JSON))

    tx = contract.functions.createNFT(token_uri).build_transaction({
        "from": WALLET_ADDRESS,
        "nonce": w3.eth.get_transaction_count(WALLET_ADDRESS),
        "gas": 300_000,
        "gasPrice": w3.eth.gas_price,
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=WALLET_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return w3.to_hex(tx_hash)


def make_qr_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0); return buf.read()

###############################################################################
# 2. DASH VORTEX VISUAL ──────────────────────────────────────────────────────
###############################################################################

def build_vortex_fig():
    import numpy as np
    theta = np.linspace(0, 8 * np.pi, 512)
    z = np.linspace(-2, 2, 512)
    r = np.linspace(0.1, 1.2, 512)
    x = r * np.cos(theta); y = r * np.sin(theta)
    return go.Figure(go.Scatter3d(x=x, y=y, z=z,
                                  mode='lines', line=dict(width=2)))

app = Flask(__name__)

# Embed Dash on /vortex/ prefix
_dash = dash.Dash(__name__, server=app, routes_pathname_prefix="/vortex/")
_dash.layout = html.Div([
    html.H3("MONSTERDOG – Vortex Viewer", className="text-white"),
    dcc.Graph(figure=build_vortex_fig())
])

###############################################################################
# 3. TEMPLATES ───────────────────────────────────────────────────────────────
###############################################################################
BASE_TPL = """<!doctype html><html class='h-full' lang='en'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<script src='https://cdn.tailwindcss.com'></script><title>MONSTERDOG NFT</title></head>
<body class='bg-zinc-900 text-zinc-100 flex flex-col items-center py-12 min-h-full'>
<h1 class='text-3xl font-bold mb-8'>MONSTERDOG ✶ NFT Mint</h1>{body}</body></html>"""

INDEX_TPL = """<form class='flex flex-col gap-4 w-full max-w-md' action='{mint_url}' method='post' enctype='multipart/form-data'>
<input name='title' placeholder='Titre' required class='p-3 rounded bg-zinc-800'>
<textarea name='description' placeholder='Description' required class='p-3 rounded bg-zinc-800'></textarea>
<input type='file' name='asset' accept='image/*' required class='file:bg-indigo-600 file:text-white file:px-4 file:py-2 file:rounded'>
<button class='bg-indigo-600 hover:bg-indigo-500 rounded py-2 font-semibold'>Mint</button></form>"""

RESULT_TPL = """<div class='bg-zinc-800 p-6 rounded-lg shadow-lg w-full max-w-xl flex flex-col gap-4'>
<h2 class='text-xl font-semibold'>NFT Minté !</h2>
<p><strong>Token URI :</strong> <a class='text-indigo-400 underline' href='{uri}' target='_blank'>{uri}</a></p>
<p><strong>Transaction :</strong> <code>{tx}</code></p>
<img class='mt-4 h-44 mx-auto' src='{qr_url}' alt='QR'>
<a class='mt-6 bg-indigo-600 hover:bg-indigo-500 text-center rounded py-2 font-semibold' href='/'>← Nouveau mint</a></div>"""

###############################################################################
# 4. ROUTES ─────────────────────────────────────────────────────────────────--
###############################################################################

@app.route("/")
def index():
    return BASE_TPL.format(body=INDEX_TPL.format(mint_url=url_for('mint')))

@app.route("/mint", methods=["POST"])
def mint():
    f = request.files.get("asset")
    if not f:
        return "No file", 400
    filepath = UPLOAD_DIR / f"{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{f.filename}"
    f.save(filepath)

    # IPFS
    asset_uri = upload_to_ipfs(filepath)
    meta = {
        "name": request.form.get("title", "Artwork"),
        "description": request.form.get("description", ""),
        "image": asset_uri,
        "timestamp": dt.datetime.utcnow().isoformat(),
    }
    meta_file = filepath.with_suffix('.json'); meta_file.write_text(json.dumps(meta))
    token_uri = upload_to_ipfs(meta_file)

    # Mint
    tx_hash = mint_nft(token_uri)

    # QR
    qr_bytes = make_qr_bytes(token_uri)
    qr_name = f"qr_{meta_file.stem}.png"; (UPLOAD_DIR / qr_name).write_bytes(qr_bytes)
    body = RESULT_TPL.format(uri=token_uri, tx=tx_hash, qr_url=url_for('qr', name=qr_name))
    return BASE_TPL.format(body=body)

@app.route("/qr/<name>")
def qr(name):
    p = UPLOAD_DIR / name
    return send_file(p, mimetype="image/png") if p.exists() else ("404", 404)

###############################################################################
# 5. ENTRY POINT ─────────────────────────────────────────────────────────────
###############################################################################

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

###############################################################################
# 6. DOCKER & COMPOSE (SAVE AS SEPARATE FILES) ─────────────────────────────--
###############################################################################

DOCKERFILE = """
# Dockerfile – MonsterDog NFT Interface
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir flask qrcode pillow ipfshttpclient web3 dash plotly
ENV PORT=5000
EXPOSE 5000
CMD ["python", "flask_nft_interface.py"]
"""

DOCKER_COMPOSE = """
version: '3.9'
services:
  nft-interface:
    build: .
    ports:
      - "5000:5000"
    environment:
      - WEB3_PROVIDER_URI=https://rpc.ankr.com/eth_sepolia
      - CONTRACT_ADDRESS=0x...
      - CONTRACT_ABI_JSON=[...]  # paste ABI here
      - WALLET_PRIVATE_KEY=${WALLET_PRIVATE_KEY}
      - WALLET_PUBLIC_ADDRESS=${WALLET_PUBLIC_ADDRESS}
    volumes:
      - ./uploads:/tmp/monsterdog_uploads
    depends_on: []
"""


