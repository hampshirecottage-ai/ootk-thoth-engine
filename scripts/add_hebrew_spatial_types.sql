-- Extend correspondences table with spatial dimensions
ALTER TABLE correspondences
ADD COLUMN IF NOT EXISTS spatial_type VARCHAR(20),     -- 'Mother_Axis', 'Double_Direction', 'Simple_Edge'
ADD COLUMN IF NOT EXISTS spatial_dimension VARCHAR(50); -- Specific spatial vector/axis

-- Seed Mother Letters (3 Primary Spatial Axes)
UPDATE correspondences SET spatial_type = 'Mother_Axis', spatial_dimension = 'Vertical Axis (Height/Depth)' WHERE hebrew_letter = 'Aleph';
UPDATE correspondences SET spatial_type = 'Mother_Axis', spatial_dimension = 'Horizontal Axis (Width/Breadth)' WHERE hebrew_letter = 'Mem';
UPDATE correspondences SET spatial_type = 'Mother_Axis', spatial_dimension = 'Longitudinal Axis (Length/Depth)' WHERE hebrew_letter = 'Shin';

-- Seed Double Letters (7 Cardinal Spatial Directions / Boundaries)
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'Up (Zenith)' WHERE hebrew_letter = 'Beth';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'Down (Nadir)' WHERE hebrew_letter = 'Gimel';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'East' WHERE hebrew_letter = 'Daleth';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'West' WHERE hebrew_letter = 'Kaph';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'North' WHERE hebrew_letter = 'Peh';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'South' WHERE hebrew_letter = 'Resh';
UPDATE correspondences SET spatial_type = 'Double_Direction', spatial_dimension = 'Center Core (Holy Temple)' WHERE hebrew_letter = 'Tav';

-- Seed Simple Letters (12 Polyhedral Edges / Sub-Directions)
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'North-East Edge' WHERE hebrew_letter = 'Heh';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'South-East Edge' WHERE hebrew_letter = 'Vav';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-East Edge' WHERE hebrew_letter = 'Zain';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-East Edge' WHERE hebrew_letter = 'Cheth';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'North-West Edge' WHERE hebrew_letter = 'Teth';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'South-West Edge' WHERE hebrew_letter = 'Yod';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-West Edge' WHERE hebrew_letter = 'Lamed';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-West Edge' WHERE hebrew_letter = 'Nun';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-North Edge' WHERE hebrew_letter = 'Samekh';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-North Edge' WHERE hebrew_letter = 'Ayin';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Upper-South Edge' WHERE hebrew_letter = 'Tzaddi';
UPDATE correspondences SET spatial_type = 'Simple_Edge', spatial_dimension = 'Lower-South Edge' WHERE hebrew_letter = 'Qoph';
