from flask import Flask, request, render_template
import pandas as pd
import math

app = Flask(__name__)

# Load the dataset
df = pd.read_csv('processed_openipf_2024_10_26.csv')

# Constants for GL Points formula for males and females
constants = {
    "M": {
        "A": 1199.72839,
        "B": 1025.18162,
        "C": 0.00921
    },
    "F": {
        "A": 610.32796,
        "B": 1045.59282,
        "C": 0.03048
    }
}

# GL Points calculation function
def calculate_gl_points(lift, bodyweight, Sex):
    A = constants[Sex]["A"]
    B = constants[Sex]["B"]
    C = constants[Sex]["C"]
    return lift * 100 / (A - B * math.exp(-C * bodyweight))

# Function to calculate rank for a selected lift
def get_percentage_rank(lift, bodyweight, lift_type, Sex):
    gl_points = calculate_gl_points(lift, bodyweight, Sex)
    column_mapping = {
        "Squat": ("SQGL", "GL S % from best"),
        "Bench": ("BGL", "GL B % from best"),
        "Deadlift": ("DLGL", "GL D % from best"),
        "Total": ("TPT T", "GL T % from best")
    }
    gl_points_column, percentage_column = column_mapping[lift_type]
    sorted_df = df[df['Sex'] == Sex].sort_values(by=gl_points_column, ascending=False)
    rank = sorted_df[gl_points_column].rank(pct=True)
    rank_value = rank[sorted_df[gl_points_column] <= gl_points].max()
    lifter_percentage_rank = rank_value * 100
	
    # Correcting strength level classification based on updated thresholds
    if lifter_percentage_rank < 20:
        strength_level = "Beginner"
    elif lifter_percentage_rank < 50:
        strength_level = "Novice"
    elif lifter_percentage_rank < 80:
        strength_level = "Intermediate"
    elif lifter_percentage_rank < 94:
        strength_level = "Advanced"
    else:
        strength_level = "Elite"

    return lifter_percentage_rank, strength_level

# Function to calculate stars based on percentage rank
def calculate_stars(percentage):
    if percentage < 10:
        return 0.5
    elif percentage < 20:
        return 1
    elif percentage < 30:
        return 1.5
    elif percentage < 40:
        return 2
    elif percentage < 65:
        return 2.5
    elif percentage < 79:
        return 3
    elif percentage < 87:
        return 3.5
    elif percentage < 94:
        return 4
    elif percentage < 97:
        return 4.5
    else:
        return 5

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        bodyweight = float(request.form["bodyweight"])
        lift = float(request.form["lift"])
        lift_type = request.form["lift_type"]
        Sex = request.form["Sex"]

        # Handle 'shemale' option as 'male'
        if Sex == "shemale":
            Sex = "M"  # Treat 'shemale' as 'M' (Male)

        # Compute rank and strength level
        lifter_percentage_rank, strength_level = get_percentage_rank(lift, bodyweight, lift_type, Sex)
        stars = calculate_stars(lifter_percentage_rank)

        result = {
            "lift": lift,
            "bodyweight": bodyweight,
            "lifter_percentage_rank": round(lifter_percentage_rank, 1),
            "strength_level": strength_level,
            "lift_type": lift_type,
            "stars": stars
        }

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)
