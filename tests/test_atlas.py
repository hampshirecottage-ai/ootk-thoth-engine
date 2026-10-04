"""ootk.atlas: where a card sits on the Tree, the cube, the zodiac, the solids and the
elemental grid. Database-free; tests/test_db_integration.py checks the frames against SQL."""
from ootk import atlas


def row(**kw):
    base = {"title": "X", "arcana_type": "Major", "suit": None, "number_or_rank": None,
            "key_scale": None, "path_or_sephira": "", "hebrew_letter": "N/A", "attribution": "",
            "spatial_dimension": None, "platonic_solid": None, "solid_faces": None,
            "solid_vertices": None, "dual_solid": None, "attributions": {}, "king_scale_color": None}
    base.update(kw)
    return base


EMPEROR = row(title="IV - The Emperor", key_scale=28, hebrew_letter="צ (Tzaddi)", attribution="Aries",
              spatial_dimension="Upper-South Edge", platonic_solid="Tetrahedron", solid_faces=4,
              solid_vertices=4, dual_solid="Tetrahedron (Self-Dual)")


def test_decans_follow_book_t():
    assert atlas.DECAN_RULERS[:3] == ("Mars", "Sun", "Venus")          # 2, 3, 4 of Wands
    assert atlas.DECAN_RULERS[12] == "Saturn"                          # 5 of Wands, Saturn in Leo
    assert atlas.decan_pip(0) == ("Wands", 2) and atlas.decan_pip(12) == ("Wands", 5)
    assert atlas.decan_pip(35) == ("Cups", 10)                         # Mars in Pisces
    assert sorted(atlas.decan_pip(i) for i in range(36)) == sorted(
        (s, n) for s in ("Wands", "Cups", "Swords", "Disks") for n in range(2, 11))


def test_major_places():
    a = atlas.card_atlas(EMPEROR, {})
    assert a["tree"]["path"] == 28 and "Netzach and Yesod" in a["tree"]["note"]
    assert a["cube"]["place"] == "Upper-South Edge" and not a["cube"]["derived"]
    assert a["zodiac"]["decans"] == [0, 1, 2] and a["zodiac"]["arcs"] == [[0, 30]]
    assert a["solid"]["edges"] == 6
    assert a["grid"] == {"row": "Fire", "col": None, "note": a["grid"]["note"]}


def test_planet_and_element_majors_cover_their_decans_and_signs():
    sun = atlas.card_atlas(row(title="XIX - The Sun", key_scale=30, attribution="Sun"), {})
    assert sun["zodiac"]["decans"] == [i for i, p in enumerate(atlas.DECAN_RULERS) if p == "Sun"]
    fool = atlas.card_atlas(row(title="0 - The Fool", key_scale=11, attribution="Air"), {})
    assert fool["zodiac"]["arcs"] == [[60, 90], [180, 210], [300, 330]]   # Gemini, Libra, Aquarius


def test_pip_sits_on_its_sephira_and_reaches_the_cube_through_its_sign():
    carriers = atlas.sign_carriers([EMPEROR])
    pip = atlas.card_atlas(row(title="3 of Wands - Virtue", arcana_type="Minor", suit="Wands",
                               number_or_rank="3", key_scale=3, attribution="Sun in Aries"), carriers)
    assert pip["tree"] == {"path": None, "sephira": [3], "note": pip["tree"]["note"]}
    assert pip["zodiac"]["decans"] == [1] and "10° to 20°" in pip["zodiac"]["note"]
    assert pip["cube"]["place"] == "Upper-South Edge" and pip["cube"]["derived"]
    assert "The Emperor" in pip["cube"]["note"]
    ace = atlas.card_atlas(row(title="Ace of Wands", arcana_type="Minor", suit="Wands", number_or_rank="1",
                               key_scale=1, attribution="Root of the Powers of Fire"), carriers)
    assert ace["tree"]["sephira"] == [1] and ace["zodiac"]["decans"] == [] and ace["cube"]["place"] is None


def test_courts_span_thirty_degrees_or_a_quadrant():
    queen = atlas.card_atlas(row(title="Queen of Wands", arcana_type="Court", suit="Wands", number_or_rank="Queen",
                                 key_scale=28, attribution="Water of Fire - 20° Pisces to 20° Aries"), {})
    assert queen["zodiac"]["arcs"] == [[350, 380]] and queen["zodiac"]["decans"] == [35, 0, 1]
    assert queen["tree"]["path"] == 28 and queen["tree"]["sephira"] == [3]          # Binah
    assert queen["grid"]["row"] == "Fire" and queen["grid"]["col"] == "Water"
    princess = atlas.card_atlas(row(title="Princess of Wands", arcana_type="Court", suit="Wands",
                                    number_or_rank="Princess", key_scale=31,
                                    attribution="Earth of Fire - Cancer, Leo, Virgo quadrant"), {})
    assert princess["zodiac"]["arcs"] == [[90, 180]] and princess["tree"]["sephira"] == [10]


def test_french_rows_name_their_path():
    fr = atlas.card_atlas(row(title="IV - The Emperor", key_scale=28, path_or_sephira="Path 14 (Chokmah-Binah)",
                              hebrew_letter="Daleth (ד)", attribution="Aries", spatial_dimension="East"), {})
    assert fr["tree"]["path"] == 14
    assert fr["cube"]["note"].startswith("The east face")
