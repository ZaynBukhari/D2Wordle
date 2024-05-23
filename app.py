from flask import Flask, jsonify, render_template, request
from bungie_api import get_legendary_guns
import random
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TARGET_GUN = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/guns', methods=['GET'])
def get_guns():
    guns = get_legendary_guns()
    logger.debug(f"Guns fetched: {len(guns)}")
    return jsonify(guns)

@app.route('/api/set_target_gun', methods=['GET'])
def set_target_gun():
    global TARGET_GUN
    guns = get_legendary_guns()
    if guns:
        TARGET_GUN = random.choice(guns)
        logger.debug(f'Target Gun: {TARGET_GUN}')  # Debugging line to log the target weapon
        return jsonify(TARGET_GUN)
    else:
        return jsonify({'error': 'No guns available'}), 500

@app.route('/api/compare', methods=['POST'])
def compare_guns():
    guessed_gun_id = request.json['guessed_gun_id']
    guns = get_legendary_guns()
    logger.debug(f"Guns available for comparison: {len(guns)}")
    try:
        guessed_gun = next(gun for gun in guns if gun['hash'] == guessed_gun_id)
        logger.debug(f'Guessed Gun: {guessed_gun}')  # Debugging line to log the guessed gun

        result = {
            'name': guessed_gun['name'],
            'icon': guessed_gun['icon'],
            'iconWatermark': guessed_gun.get('iconWatermark', ''),
            'weaponType': {'actual': guessed_gun['type'], 'correct': guessed_gun['type'] == TARGET_GUN['type']},
            'archetype': {'actual': guessed_gun['archetype'], 'correct': guessed_gun['archetype'] == TARGET_GUN['archetype']},
            'damageType': {'actual': guessed_gun['damageType'], 'correct': guessed_gun['damageType'] == TARGET_GUN['damageType']},
            'ammoType': {'actual': guessed_gun['ammoType'], 'correct': guessed_gun['ammoType'] == TARGET_GUN['ammoType']},
            'craftable': {'actual': guessed_gun['craftable'], 'correct': guessed_gun['craftable'] == TARGET_GUN['craftable']},
        }
        return jsonify(result)
    except StopIteration:
        logger.error(f"Guessed gun with ID {guessed_gun_id} not found")
        return jsonify({'error': 'Guessed gun not found'}), 400

if __name__ == '__main__':
    app.run(debug=True)
