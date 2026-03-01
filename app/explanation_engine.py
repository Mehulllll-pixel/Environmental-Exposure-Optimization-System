def generate_explanation(best_row, city_avg_pevi, distance):

    pevi_diff = round((city_avg_pevi - best_row["PEVI_adjusted"]) / city_avg_pevi * 100, 2)

    explanation = {
        "pollution_advantage_percent": pevi_diff,
        "distance_km": round(distance, 2),
        "summary": f"Recommended because pollution is {pevi_diff}% lower than city average with distance of {round(distance,2)} km."
    }

    return explanation