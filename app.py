from flask import Flask, request, render_template
import pandas as pd
import os
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
            "Squat": ("SQGL", ""),
            "Bench": ("BGL", ""),
            "Deadlift": ("DLGL", ""),
            "Total": ("TGL", "")
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

	# 1RM calculator functions
def brzycki_1rm(weight, reps):
    return weight * (36 / (37 - reps))

def epley_1rm(weight, reps):
    return weight * (1 + (0.0333 * reps))	
		
# Route for the About page
@app.route("/about")
def about():
    return render_template("about.html")

# Route for the Strength Categories page
@app.route("/strength-categories")  # Note the hyphen instead of underscore
def strength_categories():
    return render_template("strength_categories.html")

@app.route("/", methods=["GET", "POST"])
def index():
    result = None  # Initialize the result variable
    if request.method == "POST":
        try:
            # Read input data
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

            # Mapping of Division abbreviations to full names
            division_map = {
                "Overall": "Overall",
                "SJ": "Sub-Junior",
                "J": "Junior",
                "O": "Open",
                "M1": "Master I",
                "M2": "Master II",
                "M3": "Master III",
                "M4": "Master IV"
            }

            # Get the full name of the division
            full_division = division_map.get(division, division)

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
                "division": full_division,  # Use full division name
                "Sex": full_sex,
                "stars": stars,
                "lift_unit": lift_unit,  # User's selected unit (kg/lbs)
                "bodyweight_unit": bodyweight_unit  # User's selected unit (kg/lbs)
            }
        except Exception as e:
            result = {"error": f"An error occurred: {str(e)}"}

    # Always return the template with the result
    return render_template("index.html", result=result)	
	
# Route for the 1RM calculator page
@app.route("/1rm_calculator", methods=["GET", "POST"])
def one_rm_calculator():
    result = None
    if request.method == "POST":
        try:
            weight = float(request.form["weight"])
            reps = int(request.form["reps"])
            formula = request.form["formula"]
            weight_unit = request.form["weight_unit"]  # Retrieve the selected unit from the form

            # Calculate 1RM based on the selected formula
            if formula == "Brzycki":
                one_rm = brzycki_1rm(weight, reps)
            elif formula == "Epley":
                one_rm = epley_1rm(weight, reps)
            
            result = {
                "weight": weight,
                "reps": reps,
                "formula": formula,
                "one_rm": round(one_rm, 2),
                "weight_unit": weight_unit  # Include weight_unit in the result dictionary
            }
        except Exception as e:
            result = {"error": f"An error occurred: {str(e)}"}
    
    return render_template("1rm_calculator.html", result=result)
	
# Function to convert kg to lbs
def kg_to_lbs(kg):
    return kg * 2.20462

# Function to convert lbs to kg
def lbs_to_kg(lbs):
    return lbs / 2.20462

@app.route("/standards", methods=["GET", "POST"])
def standards():
    result_table = None
    result = None  # Initialize result to store selected form values
    
    if request.method == "POST":
        try:
            sex = request.form["Sex"]
            division = request.form["division"]
            lift_type = request.form["lift_type"]
            weight_unit = request.form["weight_unit"]

            # Load the CSV file for the selected category (Sex, Division, Lift Type)
            file_name = f"{sex}_{division}_{lift_type}.csv"
            file_path = os.path.join('lift_weights_by_category', file_name)

            if os.path.exists(file_path):
                df_standards = pd.read_csv(file_path)
                
                if 'Unnamed: 0' in df_standards.columns:
                    df_standards.rename(columns={'Unnamed: 0': 'Bodyweight'}, inplace=True)

                df_standards.reset_index(drop=True, inplace=True)

                # If weight_unit is lbs, convert all bodyweight values to lbs
                if weight_unit == 'lbs':
                    df_standards['Bodyweight'] = df_standards['Bodyweight'].apply(kg_to_lbs)
                    # Assuming other columns also represent weight and need conversion
                    for col in df_standards.columns:
                        if col != 'Bodyweight':  # Skip the bodyweight column
                            df_standards[col] = df_standards[col].apply(kg_to_lbs)

                # Apply rounding to all numeric values
                df_standards = df_standards.applymap(lambda x: round(x, 1) if isinstance(x, (int, float)) else x)

                result_table = df_standards.to_html(classes="table table-striped", index=False)
            
            # Store the selected form values in result
            result = {
                "Sex": sex,
                "division": division,
                "lift_type": lift_type,
                "weight_unit": weight_unit  # Add weight_unit to result
            }
            
        except Exception as e:
            result_table = f"An error occurred: {str(e)}"
    
    # Pass result back to the template along with the table
    return render_template("standards.html", result_table=result_table, result=result)

if __name__ == "__main__":
    app.run(debug=True)