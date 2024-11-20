from flask import Flask, request, render_template
import pandas as pd
import math

app = Flask(__name__)

# Load the dataset
df = pd.read_csv('processed_openipf_2024_10_26_with_division_and_sex_overall.csv')

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

# Conversion functions
def kg_to_lbs(kg):
    return kg * 2.20462

def lbs_to_kg(lbs):
    return lbs / 2.20462

# GL Points calculation function
def calculate_gl_points(lift, bodyweight, Sex):
    A = constants[Sex]["A"]
    B = constants[Sex]["B"]
    C = constants[Sex]["C"]
    return lift * 100 / (A - B * math.exp(-C * bodyweight))

# Function to calculate rank for a selected lift and division
def get_percentage_rank(lift, bodyweight, lift_type, Sex, division):
    gl_points = calculate_gl_points(lift, bodyweight, Sex)
    column_mapping = {
        "Squat": ("SQGL", f"SQPct_{division}"),
        "Bench": ("BGL", f"BPct_{division}"),
        "Deadlift": ("DLGL", f"DLPct_{division}"),
        "Total": ("TGL", f"TPct_{division}")
    }

    # Use overall percentage if 'Overall' is selected
    if division == "Overall":
        column_mapping = {
            "Squat": ("SQGL", "GL S % from best"),
            "Bench": ("BGL", "GL B % from best"),
            "Deadlift": ("DLGL", "GL D % from best"),
            "Total": ("TGL", "GL T % from best")
        }

    gl_points_column, percentage_column = column_mapping[lift_type]
    sorted_df = df[(df['Sex'] == Sex) & (df['Division'] == division if division != "Overall" else True)]
    sorted_df = sorted_df.sort_values(by=gl_points_column, ascending=False)
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

# Route for the About page
@app.route("/about")
def about():
    return render_template("about.html")

# Route for the Home page (Powerlifting Standards)		
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        bodyweight = float(request.form["bodyweight"])
        lift = float(request.form["lift"])
        lift_type = request.form["lift_type"]
        Sex = request.form["Sex"]
        division = request.form["division"]
        lift_unit = request.form["lift_unit"]
        bodyweight_unit = request.form["bodyweight_unit"]
		
          # Save the original values before conversion
        original_lift = lift
        original_bodyweight = bodyweight

        # Convert to kg if the unit is lbs
        if lift_unit == "lbs":
            lift = lbs_to_kg(lift)
        
        if bodyweight_unit == "lbs":
            bodyweight = lbs_to_kg(bodyweight)
		
		# Mapping of Sex values to full names
        sex_map = {
            "M": "Male",
            "F": "Female",
            "shemale": "Shemale"
        }

        # Convert short 'Sex' to full name
        full_sex = sex_map.get(Sex, Sex)  # Default to 'Sex' if it doesn't match

        # Handle 'shemale' option as 'M'
        if Sex == "shemale":
            Sex = "M"  # Treat 'shemale' as 'M' (Male)

        # Compute rank and strength level
        lifter_percentage_rank, strength_level = get_percentage_rank(lift, bodyweight, lift_type, Sex, division)
        stars = calculate_stars(lifter_percentage_rank)


        # Prepare result, include the original units used
        result = {
    "original_lift": original_lift,  # Unconverted lift in user's selected unit
    "original_bodyweight": original_bodyweight,  # Unconverted bodyweight in user's selected unit
    "lift": lift,  # Converted lift (kg)
    "bodyweight": bodyweight,  # Converted bodyweight (kg)
    "lifter_percentage_rank": round(lifter_percentage_rank, 1),
    "strength_level": strength_level,
    "lift_type": lift_type,
    "division": division,
    "Sex": full_sex,
    "stars": stars,
    "lift_unit": lift_unit,  # User's selected unit (kg/lbs)
    "bodyweight_unit": bodyweight_unit  # User's selected unit (kg/lbs)
}

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)