WAREHOUSE_COORDS = (0, 0)

AGENTS = [
    {
        'capacity': 15,
        'velocity': 1.0,
        'start_coords': (10, 10),
        'return_to_warehouse': True
    },
    {
        'capacity': 12,
        'velocity': 1.2,
        'start_coords': (-5, 5),
        'return_to_warehouse': False
    },
    {
        'capacity': 18,
        'velocity': 0.9,
        'start_coords': (5, -5),
        'return_to_warehouse': True
    },
    {
        'capacity': 10,
        'velocity': 1.5,
        'start_coords': (-10, -10),
        'return_to_warehouse': False
    },
    {
        'capacity': 20,
        'velocity': 0.8,
        'start_coords': (0, 15),
        'return_to_warehouse': True
    }
]

PARCELS = [
    {'coords': (2, 3), 'weight': 2, 'delivery_window': (0, 100)},
    {'coords': (5, 7), 'weight': 3, 'delivery_window': (0, 120)},
    {'coords': (-3, 2), 'weight': 1, 'delivery_window': (30, 90)},
    {'coords': (-4, -1), 'weight': 4, 'delivery_window': (20, 80)},
    {'coords': (1, -5), 'weight': 2, 'delivery_window': (40, 100)},
    {'coords': (8, 3), 'weight': 1, 'delivery_window': (10, 50)},
    {'coords': (-2, -6), 'weight': 3, 'delivery_window': (60, 120)},
    {'coords': (4, 2), 'weight': 5, 'delivery_window': (0, 60)},
    {'coords': (-7, 3), 'weight': 2, 'delivery_window': (40, 90)},
    {'coords': (3, -4), 'weight': 1, 'delivery_window': (30, 80)},
    {'coords': (-5, -2), 'weight': 3, 'delivery_window': (20, 70)},
    {'coords': (6, 1), 'weight': 4, 'delivery_window': (50, 110)},
    {'coords': (-1, 5), 'weight': 2, 'delivery_window': (10, 90)},
    {'coords': (2, -7), 'weight': 1, 'delivery_window': (80, 140)},
    {'coords': (-3, -4), 'weight': 5, 'delivery_window': (40, 100)},
    {'coords': (7, 4), 'weight': 2, 'delivery_window': (30, 70)},
    {'coords': (-6, 1), 'weight': 3, 'delivery_window': (60, 120)},
    {'coords': (4, -3), 'weight': 1, 'delivery_window': (20, 80)},
    {'coords': (-2, 8), 'weight': 4, 'delivery_window': (0, 100)},
    {'coords': (5, -6), 'weight': 2, 'delivery_window': (50, 110)},
    {'coords': (-8, -3), 'weight': 5, 'delivery_window': (30, 90)},
    {'coords': (3, 6), 'weight': 1, 'delivery_window': (10, 70)},
    {'coords': (-1, -8), 'weight': 3, 'delivery_window': (20, 80)},
    {'coords': (6, -2), 'weight': 2, 'delivery_window': (40, 100)},
    {'coords': (-4, 7), 'weight': 4, 'delivery_window': (50, 120)}
]

# Validation checks
assert len(AGENTS) == 5, "Should be 5 agents"
assert len(PARCELS) == 25, "Should be 25 parcels"
for p in PARCELS:
    assert p['weight'] > 0, "Parcel weight must be positive"
    assert p['delivery_window'][0] < p['delivery_window'][1], "Invalid delivery window"
for a in AGENTS:
    assert a['capacity'] > 0, "Agent capacity must be positive"
    assert a['velocity'] > 0, "Agent velocity must be positive"
