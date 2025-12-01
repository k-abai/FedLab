import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# NFL field dimensions in yards (including end zones)
FIELD_LENGTH = 120  # 0–10 endzone, 10–110 field, 110–120 endzone
FIELD_WIDTH = 53.3  # standard width


def load_players(csv_path, n_per_side=11, random_state=0):
    """
    Load a subset of players from the cleaned tracking CSV.

    Expected columns in CSV:
        x, y, player_side, s, a, o

    player_side should contain "Offense" or "Defense".
    """
    df = pd.read_csv(csv_path)

    players_list = []
    for side in ["Offense", "Defense"]:
        side_df = df[df["player_side"] == side]
        if side_df.empty:
            continue
        take = min(n_per_side, len(side_df))
        sampled = side_df.sample(n=take, random_state=random_state)
        players_list.append(sampled)

    if not players_list:
        raise ValueError(
            "No players found in CSV with player_side 'Offense' or 'Defense'."
        )

    players = pd.concat(players_list, ignore_index=True)
    return players


def prepare_state(players):
    """
    Build initial state arrays from the player dataframe.

    Uses:
        x, y   - starting position on field (yards)
        s      - speed (yards / second)
        a      - acceleration magnitude (yards / second^2)
        o      - orientation angle (degrees, 0 = right, 90 = up)

    We assume velocity and acceleration are along orientation o.
    """
    x0 = players["x"].to_numpy(dtype=float)
    y0 = players["y"].to_numpy(dtype=float)
    s = players["s"].to_numpy(dtype=float)
    a = players["a"].to_numpy(dtype=float)
    o_deg = players["o"].to_numpy(dtype=float)

    # Convert orientation to radians
    theta = np.deg2rad(o_deg)

    # Initial velocity components based on speed and orientation
    vx0 = s * np.cos(theta)
    vy0 = s * np.sin(theta)

    # Acceleration components, also along heading
    ax = a * np.cos(theta)
    ay = a * np.sin(theta)

    side = players["player_side"].to_numpy()

    return x0, y0, vx0, vy0, ax, ay, side, s, a, theta


def simulate_positions(x0, y0, vx0, vy0, ax, ay, t):
    """
    Simple constant-acceleration motion model:
        x(t) = x0 + v0 * t + 0.5 * a * t^2
    """
    x = x0 + vx0 * t + 0.5 * ax * t**2
    y = y0 + vy0 * t + 0.5 * ay * t**2
    return x, y


def animate_play(csv_path="cleaned_data.csv",
                 n_per_side=11,
                 dt=0.1,
                 n_frames=100):
    """
    Run an animated simulation:
      - starting positions from (x, y)
      - movement derived from s, a, and o
      - offense = red circles, defense = blue X
      - arrows show direction (o), length scaled by s, color = a

    Returns
    -------
    anim : matplotlib.animation.FuncAnimation
        The animation object (must be kept alive by caller).
    """
    players = load_players(csv_path, n_per_side=n_per_side)
    x0, y0, vx0, vy0, ax, ay, side, speed, acc, theta = prepare_state(players)

    fig, ax_plot = plt.subplots(figsize=(12, 6))
    ax_plot.set_xlim(0, FIELD_LENGTH)
    ax_plot.set_ylim(0, FIELD_WIDTH)
    ax_plot.set_aspect('equal', adjustable='box')
    ax_plot.set_xlabel("Field X (yards)")
    ax_plot.set_ylabel("Field Y (yards)")
    ax_plot.set_title("NFL Player Movement Simulation")

    # Draw basic field lines (origin at bottom-left)
    ax_plot.axvline(0, color="k")
    ax_plot.axvline(10, color="k", linestyle="--", alpha=0.3)   # left endzone
    ax_plot.axvline(110, color="k", linestyle="--", alpha=0.3)  # right endzone
    ax_plot.axvline(120, color="k")
    for x_line in range(10, 120, 10):
        ax_plot.axvline(x_line, color="gray", linestyle=":", alpha=0.2)

    # Masks for offense/defense
    offense_mask = side == "Offense"
    defense_mask = side == "Defense"

    # Scatter plots: offense red circles, defense blue X
    offense_scatter = ax_plot.scatter(
        x0[offense_mask],
        y0[offense_mask],
        c="red",
        marker="o",
        label="Offense"
    )
    defense_scatter = ax_plot.scatter(
        x0[defense_mask],
        y0[defense_mask],
        c="blue",
        marker="x",
        label="Defense"
    )

    # Orientation / velocity arrows (quiver)
    # Arrow direction = orientation (theta)
    # Arrow length proportional to speed
    arrow_scale = 0.2  # tweak if arrows are too long/short
    u = np.cos(theta) * speed * arrow_scale
    v = np.sin(theta) * speed * arrow_scale

    quiver = ax_plot.quiver(
        x0,
        y0,
        u,
        v,
        acc,                 # colors represent acceleration magnitude
        cmap="coolwarm",
        angles="xy",
        scale_units="xy",
        scale=1,
        width=0.005
    )

    fig.colorbar(quiver, ax=ax_plot, label="Acceleration (a)")

    # Time text box
    time_text = ax_plot.text(
        0.02, 0.95, "",
        transform=ax_plot.transAxes,
        fontsize=12,
        bbox=dict(facecolor="white", alpha=0.7, edgecolor="none")
    )

    ax_plot.legend(loc="upper right")

    def init():
        time_text.set_text("t = 0.00 s")
        return offense_scatter, defense_scatter, quiver, time_text

    def update(frame_idx):
        t = frame_idx * dt
        x, y = simulate_positions(x0, y0, vx0, vy0, ax, ay, t)

        # Keep everyone on the visible field for visualization (clip to bounds)
        x_clipped = np.clip(x, 0, FIELD_LENGTH)
        y_clipped = np.clip(y, 0, FIELD_WIDTH)

        # Update scatter offsets
        offense_scatter.set_offsets(
            np.c_[x_clipped[offense_mask], y_clipped[offense_mask]]
        )
        defense_scatter.set_offsets(
            np.c_[x_clipped[defense_mask], y_clipped[defense_mask]]
        )

        # Update arrow positions
        quiver.set_offsets(np.c_[x_clipped, y_clipped])

        # Arrows keep same direction/length (based on starting speed/orientation)
        u = np.cos(theta) * speed * arrow_scale
        v = np.sin(theta) * speed * arrow_scale
        quiver.set_UVC(u, v, acc)

        time_text.set_text(f"t = {t:.2f} s")
        return offense_scatter, defense_scatter, quiver, time_text

    anim = FuncAnimation(
        fig,
        update,
        frames=n_frames,
        init_func=init,
        blit=False,
        interval=50,   # ms between frames
        repeat=True
    )

    # IMPORTANT: don't call plt.show() here – just return the animation.
    return anim


if __name__ == "__main__":
    # Adjust csv_path if your file has a different name or location
    anim = animate_play(
        csv_path="cleaned_data.csv",
        n_per_side=11,
        dt=0.1,
        n_frames=150
    )

    # Keep `anim` alive and render the animation
    plt.show()
