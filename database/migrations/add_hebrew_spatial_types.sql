-- Step 1: Ensure columns exist
ALTER TABLE correspondences
ADD COLUMN IF NOT EXISTS spatial_type VARCHAR(20),     -- 'Mother_Axis', 'Double_Direction', 'Simple_Edge'
ADD COLUMN IF NOT EXISTS spatial_dimension VARCHAR(50); -- Specific spatial vector/axis

-- Step 2: Clear any existing partial data
UPDATE correspondences SET spatial_type = NULL, spatial_dimension = NULL;

-- Step 3: Mother Letters (3 Primary Spatial Axes)
-- Key Scale 11 (Aleph), 23 (Mem), 31 (Shin)
UPDATE correspondences SET spatial_type = 'Mother_Axis', spatial_dimension = 'Vertical Axis (Height/Depth)' WHERE key_scale = '11';
UPDATE correspondences SET spatial_type = 'Mother_Axis', spatial_dimension = 'Horizontal Axis (Width/Breadth)' WHERE key_scale = '23';
UPDATE correspondences SET spatial_type = 'Mother_Axis', spatial_dimension = 'Longitudinal Axis (Length/Depth)' WHERE key_scale = '31';

-- Step 4: Double Letters (7 Cardinal Spatial Directions / Boundaries)
-- Key Scale 12 (Beth), 13 (Gimel), 14 (Daleth), 21 (Kaph), 27 (Peh), 30 (Resh), 32 (Tav)
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'Up (Zenith)' WHERE key_scale = '12';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'Down (Nadir)' WHERE key_scale = '13';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'East' WHERE key_scale = '14';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'West' WHERE key_scale = '21';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'North' WHERE key_scale = '27';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'South' WHERE key_scale = '30';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'Center Core (Holy Temple)' WHERE key_scale = '32';

-- Step 5: Simple Letters (12 Polyhedral Edges / Sub-Directions)
-- Key Scale 15 (Heh), 16 (Vav), 17 (Zain), 18 (Cheth), 19 (Teth), 20 (Yod), 22 (Lamed), 24 (Nun), 25 (Samekh), 26 (Ayin), 28 (Tzaddi), 29 (Qoph)
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'North-East Edge' WHERE key_scale = '15';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'South-East Edge' WHERE key_scale = '16';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-East Edge' WHERE key_scale = '17';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-East Edge' WHERE key_scale = '18';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'North-West Edge' WHERE key_scale = '19';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'South-West Edge' WHERE key_scale = '20';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-West Edge' WHERE key_scale = '22';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-West Edge' WHERE key_scale = '24';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-North Edge' WHERE key_scale = '25';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-North Edge' WHERE key_scale = '26';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-South Edge' WHERE key_scale = '28';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-South Edge' WHERE key_scale = '29';
