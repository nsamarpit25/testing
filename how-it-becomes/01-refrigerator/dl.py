"""Download Poly Haven CC0 assets (gltf models at 1k, textures at 1k, HDRI at 2k) into assets/.
python3 dl.py"""
import json, os, urllib.request
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
MODELS = ["garden_gnome", "food_apple_01", "lemon", "food_lime_01", "food_pears_asian_01", "food_avocado_01", "jug_01",
          "wooden_crate_01", "wall_clock", "carrot_cake", "strawberry_chocolate_cake", "hamburger_buns", "plastic_bottle_gallon",
          "tea_set_01", "wooden_cutting_board", "vintage_electric_kettle", "potted_plant_01", "electric_stove", "yellow_onion", "CheeseBox_01"]
TEX = ["laminate_floor_02", "white_plaster_02", "long_white_tiles", "grass_ground", "weathered_plank_siding", "roof_tiles", "kitchen_wood", "oak_wood_planks"]
HDRI = "kloofendal_48d_partly_cloudy_puresky"
get = lambda u: json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "howitbecomes"})))
def fetch(url, path):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path)
for m in MODELS:
    try:
        f = get(f"https://api.polyhaven.com/files/{m}")["gltf"]["1k"]["gltf"]
    except Exception as e:
        print("skip", m, e); continue
    d = os.path.join(A, "models", m)
    fetch(f["url"], os.path.join(d, os.path.basename(f["url"])))
    for rel, inc in f.get("include", {}).items(): fetch(inc["url"], os.path.join(d, rel))
    print("model", m)
for t in TEX:
    f = get(f"https://api.polyhaven.com/files/{t}")
    for k in ["Diffuse", "nor_gl", "Rough", "arm"]:
        if k in f and "1k" in f[k]: fetch(f[k]["1k"]["jpg"]["url"], os.path.join(A, "tex", t, f"{k}.jpg"))
    print("tex", t)
fetch(get(f"https://api.polyhaven.com/files/{HDRI}")["hdri"]["2k"]["hdr"]["url"], os.path.join(A, "hdri", HDRI + ".hdr"))
print("hdri ok")
