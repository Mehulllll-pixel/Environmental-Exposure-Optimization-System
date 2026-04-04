def generate_explanation(best, avg_pevi, distance):

    if best["PEVI_adjusted"] < avg_pevi:
        return "Cleaner than average air quality."

    elif best["distance_km"] > 10:
        return "Safer but farther location selected."

    else:
        return "Balanced choice between safety and distance."