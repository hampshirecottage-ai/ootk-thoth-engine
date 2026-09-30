-- Step 1: Ensure columns exist
ALTER TABLE correspondences
ADD COLUMN IF NOT EXISTS platonic_solid VARCHAR(30),       -- Polyhedron Name
ADD COLUMN IF NOT EXISTS solid_faces INTEGER,               -- Total Faces
ADD COLUMN IF NOT EXISTS solid_vertices INTEGER,            -- Total Vertices
ADD COLUMN IF NOT EXISTS dual_solid VARCHAR(30),           -- Polyhedral Dual
ADD COLUMN IF NOT EXISTS topological_role VARCHAR(50);      -- Role

-- Step 2: Clear existing topological data to ensure a clean slate
UPDATE correspondences SET 
    platonic_solid = NULL, 
    solid_faces = NULL, 
    solid_vertices = NULL, 
    dual_solid = NULL, 
    topological_role = NULL;

-- Step 3: Sephiroth Core Matrix (Key Scales 1-10) -> Dodecahedron (Spirit / Quintessence)
UPDATE correspondences SET 
    platonic_solid = 'Dodecahedron', 
    solid_faces = 12, 
    solid_vertices = 20, 
    dual_solid = 'Icosahedron', 
    topological_role = 'Quintessential Core (12 Zodiacal Pentagons)' 
WHERE CAST(key_scale AS INTEGER) BETWEEN 1 AND 10;

-- Step 4: Fire Paths -> Tetrahedron (4 Faces / 4 Vertices)
-- Key Scales 11 (Air/Fire synthesis), 15 (Aries), 19 (Leo), 23 (Mem/Water-Fire), 25 (Sagittarius), 31 (Shin/Fire)
UPDATE correspondences SET 
    platonic_solid = 'Tetrahedron', 
    solid_faces = 4, 
    solid_vertices = 4, 
    dual_solid = 'Tetrahedron (Self-Dual)', 
    topological_role = 'Primary Ignis Vector (Expansion)' 
WHERE key_scale IN ('15', '19', '25', '31');

-- Step 5: Water Paths -> Icosahedron (20 Faces / 12 Vertices)
-- Key Scales 18 (Cancer), 23 (Water), 24 (Scorpio), 29 (Pisces)
UPDATE correspondences SET 
    platonic_solid = 'Icosahedron', 
    solid_faces = 20, 
    solid_vertices = 12, 
    dual_solid = 'Dodecahedron', 
    topological_role = 'Receptive Matrix (Fluid Volume)' 
WHERE key_scale IN ('18', '23', '24', '29');

-- Step 6: Air Paths -> Octahedron (8 Faces / 6 Vertices)
-- Key Scales 11 (Aleph/Air), 17 (Gemini), 22 (Libra), 28 (Aquarius)
UPDATE correspondences SET 
    platonic_solid = 'Octahedron', 
    solid_faces = 8, 
    solid_vertices = 6, 
    dual_solid = 'Hexahedron (Cube)', 
    topological_role = 'Dynamic Axis (Mediating Air)' 
WHERE key_scale IN ('11', '17', '22', '28');

-- Step 7: Earth Paths -> Hexahedron / Cube (6 Faces / 8 Vertices)
-- Key Scales 16 (Taurus), 20 (Virgo), 26 (Capricorn), 32 (Tav/Earth)
UPDATE correspondences SET 
    platonic_solid = 'Hexahedron (Cube)', 
    solid_faces = 6, 
    solid_vertices = 8, 
    dual_solid = 'Octahedron', 
    topological_role = 'Crystallized Vessel (Physical Boundary)' 
WHERE key_scale IN ('16', '20', '26', '32');

-- Step 8: Planetary Paths -> Dodecahedron Dual Axis (Key Scales 12, 13, 14, 21, 27, 30)
-- Beth (Mercury), Gimel (Moon), Daleth (Venus), Kaph (Jupiter), Peh (Mars), Resh (Sun)
UPDATE correspondences SET 
    platonic_solid = 'Dodecahedron', 
    solid_faces = 12, 
    solid_vertices = 20, 
    dual_solid = 'Icosahedron', 
    topological_role = 'Planetary Celestial Face' 
WHERE key_scale IN ('12', '13', '14', '21', '27', '30');
