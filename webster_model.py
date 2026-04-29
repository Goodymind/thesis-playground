def webster(arrival_interval_ns, arrival_interval_ew,
            saturation_headway, first_car_delay,
            min_green=20, max_green=160):

    v_ns = 1.0 / arrival_interval_ns
    v_ew = 1.0 / arrival_interval_ew
    s    = 1.0 / saturation_headway      # same saturation flow both directions

    y_ns = v_ns / s   # = saturation_headway / arrival_interval_ns
    y_ew = v_ew / s
    Y    = y_ns + y_ew

    L    = 2 * first_car_delay           # total lost time per cycle

    if Y >= 1.0:
        # oversaturated — Webster breaks down, return max green to dominant direction
        if y_ns >= y_ew:
            return max_green, min_green
        else:
            return min_green, max_green

    C = (1.5 * L + 5) / (1 - Y)         # optimal cycle length

    effective_green = C - L              # green time available to split
    g_ns = effective_green * (y_ns / Y)
    g_ew = effective_green * (y_ew / Y)

    # clamp to min/max and round to nearest 5
    g_ns = max(min_green, min(max_green, round(g_ns / 5) * 5))
    g_ew = max(min_green, min(max_green, round(g_ew / 5) * 5))

    return g_ns, g_ew