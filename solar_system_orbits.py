#!/usr/bin/env python3
"""
solar_system_orbits.py

Enhanced visualization of Solar System orbits plus annual Earth→Mars launch windows,
realistic Hohmann-transfer time estimates, and saved charts.

Dependencies:
    pip install skyfield matplotlib numpy

Usage:
    Animate orbits: python solar_system_orbits.py
    Compute & save windows & charts: python solar_system_orbits.py windows
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from skyfield.api import load
from datetime import datetime, timedelta
import math

# --- Configuration -----------------------------------------------------------
DAYS_PER_FRAME = 5.0           # Simulated days per frame for animation
INTERVAL_MS = 50               # Milliseconds between frames (~20 FPS)
TRAIL_LENGTH = 50              # Trail length for planet trails
STAR_COUNT = 500               # Number of stars in background
AXIS_LIMIT = 40                # AU plot limits
TARGET_PLANETS = [
    'mercury', 'venus', 'earth', 'mars',
    'jupiter barycenter', 'saturn barycenter',
    'uranus barycenter', 'neptune barycenter'
]
PLANET_COLORS = {
    'mercury': 'gray',
    'venus': 'orange',
    'earth': 'blue',
    'mars': 'red',
    'jupiter barycenter': 'saddlebrown',
    'saturn barycenter': 'gold',
    'uranus barycenter': 'lightblue',
    'neptune barycenter': 'purple'
}
# Gravitational parameter of the Sun in AU^3/day^2 (Gauss' constant squared)
GM_SUN = 0.0002959122082855911

# --- Helper Functions --------------------------------------------------------
def radial_exaggerate(x, y, max_radius=AXIS_LIMIT):
    r = np.hypot(x, y)
    if r == 0:
        return 0.0, 0.0
    r_new = np.log1p(r) / np.log1p(max_radius) * max_radius
    theta = np.arctan2(y, x)
    return r_new * np.cos(theta), r_new * np.sin(theta)

# Load ephemeris and timescale
eph = load('de421.bsp')
ts = load.timescale()

# Planet position and distance computations

def get_planet_xy(t, name):
    sun = eph['sun']
    body = eph[name]
    pos = sun.at(t).observe(body).position.au
    return pos[0], pos[1]

def earth_mars_distance(t):
    x_e, y_e = get_planet_xy(t, 'earth')
    x_m, y_m = get_planet_xy(t, 'mars')
    return np.hypot(x_m - x_e, y_m - y_e)

# Compute annual launch windows and realistic transfer times

def compute_launch_windows(start_year=2025, end_year=2045,
                          dist_chart='launch_windows.png',
                          time_chart='travel_times.png'):
    years, dates, dists = [], [], []
    for year in range(start_year, end_year + 1):
        best_date, best_dist = None, np.inf
        d0 = datetime(year, 1, 1)
        for offset in range(0, 366):
            dt = d0 + timedelta(days=offset)
            t = ts.utc(dt.year, dt.month, dt.day)
            dist = earth_mars_distance(t)
            if dist < best_dist:
                best_dist, best_date = dist, dt
        years.append(year)
        dates.append(best_date)
        dists.append(best_dist)
        print(f"{year}: closest approach on {best_date.strftime('%Y-%m-%d')} at {best_dist:.3f} AU")

    # Plot distance chart
    plt.figure(figsize=(8, 4))
    plt.plot(years, dists, marker='o', linestyle='-')
    plt.title('Annual Closest Earth→Mars Distances')
    plt.xlabel('Year')
    plt.ylabel('Distance (AU)')
    for x, y, dt in zip(years, dists, dates):
        plt.text(x, y, dt.strftime('%b %d'), fontsize=8,
                 ha='center', va='bottom')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(dist_chart, dpi=150)
    print(f"Saved distance chart to {dist_chart}")

    # Compute realistic Hohmann transfer times (days)
    transfer_days = []
    for dt in dates:
        t = ts.utc(dt.year, dt.month, dt.day)
        # radii from Sun in AU
        r_e = np.hypot(*get_planet_xy(t, 'earth'))
        r_m = np.hypot(*get_planet_xy(t, 'mars'))
        a_trans = (r_e + r_m) / 2.0  # semi-major axis of transfer ellipse
        T_days = math.pi * math.sqrt(a_trans**3 / GM_SUN)
        transfer_days.append(T_days)

    # Plot transfer time chart
    plt.figure(figsize=(8, 4))
    plt.plot(years, transfer_days, marker='o', linestyle='-')
    plt.title('Estimated Hohmann Transfer Time to Mars')
    plt.xlabel('Year')
    plt.ylabel('Transfer Time (days)')
    for x, td in zip(years, transfer_days):
        months = int(td // 30)
        days = int(td % 30)
        plt.text(x, td, f"{months}m{days}d", fontsize=8,
                 ha='center', va='bottom')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(time_chart, dpi=150)
    print(f"Saved transfer time chart to {time_chart}")

# --- Animation Setup ----------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 10))
ax.set_facecolor('k')
ax.set_aspect('equal', 'box')
ax.set_xlim(-AXIS_LIMIT, AXIS_LIMIT)
ax.set_ylim(-AXIS_LIMIT, AXIS_LIMIT)
ax.set_xlabel('AU')
ax.set_ylabel('AU')
ax.set_title('Solar System Orbits (Simulated)')

# Background stars
stars_x = np.random.uniform(-AXIS_LIMIT, AXIS_LIMIT, size=STAR_COUNT)
stars_y = np.random.uniform(-AXIS_LIMIT, AXIS_LIMIT, size=STAR_COUNT)
ax.scatter(stars_x, stars_y, s=1, color='white', alpha=0.3)

# Sun and planet markers/trails
ax.scatter(0, 0, color='yellow', s=200, label='Sun', zorder=5)
planet_scatters, planet_trails, histories = {}, {}, {}
for name in TARGET_PLANETS:
    c = PLANET_COLORS[name]
    planet_scatters[name] = ax.scatter([], [], color=c, s=80, zorder=10)
    ln, = ax.plot([], [], lw=1.5, alpha=0.7, color=c)
    planet_trails[name] = ln
    histories[name] = {'x': [], 'y': []}

date_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                    color='white', fontsize=12, va='top')

current_days = 0.0
start_time = ts.now()
def update(frame):
    global current_days
    current_days += DAYS_PER_FRAME
    t = ts.tt_jd(start_time.tt + current_days)
    for name in TARGET_PLANETS:
        rx, ry = get_planet_xy(t, name)
        x, y = radial_exaggerate(rx, ry)
        h = histories[name]
        h['x'].append(x); h['y'].append(y)
        if len(h['x']) > TRAIL_LENGTH:
            h['x'].pop(0); h['y'].pop(0)
        planet_scatters[name].set_offsets([[x, y]])
        planet_trails[name].set_data(h['x'], h['y'])
    date_text.set_text(f"Date: {ts.tt_jd(start_time.tt + current_days).utc_datetime().strftime('%Y-%m-%d')}")
    return list(planet_scatters.values()) + list(planet_trails.values()) + [date_text]

ax.legend(loc='upper right', fontsize='small', facecolor='gray', framealpha=0.3)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'windows':
        compute_launch_windows(2025, 2045)
    else:
        ani = animation.FuncAnimation(fig, update,
                                      interval=INTERVAL_MS,
                                      blit=True,
                                      cache_frame_data=False)
        plt.show()