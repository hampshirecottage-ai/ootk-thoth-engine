-- Adds thoth_cards.french_number: each Major's number in the French/Egyptian
-- (Levi/Papus) sequence, used to join that card's French correspondences row.
-- Thoth swaps VIII and XI, so Adjustment (Thoth VIII) is French 11 and Lust (Thoth XI) is French 8.
-- Minors and Courts stay NULL. Safe to re-run; only fills rows that are still NULL.

ALTER TABLE thoth_cards ADD COLUMN IF NOT EXISTS french_number integer;

UPDATE thoth_cards
SET french_number = CASE card_id
        WHEN 9  THEN 11   -- VIII - Adjustment
        WHEN 12 THEN 8    -- XI - Lust
        ELSE card_id - 1  -- 0 - The Fool (card 1) .. XXI - The Universe (card 22)
    END
WHERE arcana_type = 'Major' AND french_number IS NULL;
