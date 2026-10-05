-- Create layout position spatial definitions table
CREATE TABLE IF NOT EXISTS spread_position_geometry (
    position_id SERIAL PRIMARY KEY,
    spread_key VARCHAR(10) NOT NULL,
    position_index INT NOT NULL,
    position_name VARCHAR(100) NOT NULL,
    pos_x FLOAT NOT NULL, -- Normalized X (-1.0 to 1.0)
    pos_y FLOAT NOT NULL, -- Normalized Y (-1.0 to 1.0)
    pos_z FLOAT DEFAULT 0.0, -- Normalized Z (-1.0 to 1.0 for 3D layouts)
    polar_angle_deg FLOAT -- Angle in degrees (0 - 360) for circular/astrological layouts
);

-- Seed Coordinates for Spread 6: Golden Dawn hexagram, planets as on the Tree of Life
-- (the layout ootk.spreads draws): Saturn top, Jupiter and Venus right, Mars and Mercury
-- left, Sun in the centre, Moon at the bottom.
INSERT INTO spread_position_geometry (spread_key, position_index, position_name, pos_x, pos_y, polar_angle_deg) VALUES
('6', 1, 'Saturn (Top Apex)', 0.0, 1.0, 90.0),
('6', 2, 'Jupiter (Right Top)', 0.866, 0.5, 30.0),
('6', 3, 'Mars (Left Top)', -0.866, 0.5, 150.0),
('6', 4, 'Venus (Right Bottom)', 0.866, -0.5, 330.0),
('6', 5, 'Mercury (Left Bottom)', -0.866, -0.5, 210.0),
('6', 6, 'Sun (Center Core)', 0.0, 0.0, 0.0),
('6', 7, 'Moon (Bottom Apex)', 0.0, -1.0, 270.0);

-- Seed Coordinates for Spread 10: 12 Zodiacal Signs (Circle division by 30 deg)
INSERT INTO spread_position_geometry (spread_key, position_index, position_name, pos_x, pos_y, polar_angle_deg) VALUES
('10', 1, 'Aries', 1.0, 0.0, 0.0),
('10', 2, 'Taurus', 0.866, 0.5, 30.0),
('10', 3, 'Gemini', 0.5, 0.866, 60.0),
('10', 4, 'Cancer', 0.0, 1.0, 90.0),
('10', 5, 'Leo', -0.5, 0.866, 120.0),
('10', 6, 'Virgo', -0.866, 0.5, 150.0),
('10', 7, 'Libra', -1.0, 0.0, 180.0),
('10', 8, 'Scorpio', -0.866, -0.5, 210.0),
('10', 9, 'Sagittarius', -0.5, -0.866, 240.0),
('10', 10, 'Capricorn', 0.0, -1.0, 270.0),
('10', 11, 'Aquarius', 0.5, -0.866, 300.0),
('10', 12, 'Pisces', 0.866, -0.5, 330.0);
