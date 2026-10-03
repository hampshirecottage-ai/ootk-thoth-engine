--
-- PostgreSQL database dump
--

\restrict TlcpppKLPezyITSwjwz9FNdJjzIqpmcAjeKjG6oYwPiHoUfzo7TEzYsYAcoSn51

-- Dumped from database version 17.11 (Homebrew)
-- Dumped by pg_dump version 17.11 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.spread_pulls DROP CONSTRAINT IF EXISTS spread_pulls_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_card_pulls DROP CONSTRAINT IF EXISTS session_card_pulls_spread_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_card_pulls DROP CONSTRAINT IF EXISTS session_card_pulls_session_id_fkey;
ALTER TABLE IF EXISTS ONLY public.session_card_pulls DROP CONSTRAINT IF EXISTS session_card_pulls_card_id_fkey;
DROP INDEX IF EXISTS public.idx_cards_key_scale;
DROP INDEX IF EXISTS public.idx_cards_fts;
ALTER TABLE IF EXISTS ONLY public.thoth_cards DROP CONSTRAINT IF EXISTS unique_card_title;
ALTER TABLE IF EXISTS ONLY public.thoth_cards DROP CONSTRAINT IF EXISTS thoth_cards_pkey1;
ALTER TABLE IF EXISTS ONLY public.tarot_sessions DROP CONSTRAINT IF EXISTS tarot_sessions_pkey;
ALTER TABLE IF EXISTS ONLY public.spread_pulls DROP CONSTRAINT IF EXISTS spread_pulls_pkey;
ALTER TABLE IF EXISTS ONLY public.spread_position_geometry DROP CONSTRAINT IF EXISTS spread_position_geometry_pkey;
ALTER TABLE IF EXISTS ONLY public.session_card_pulls DROP CONSTRAINT IF EXISTS session_card_pulls_pkey;
ALTER TABLE IF EXISTS ONLY public.correspondences DROP CONSTRAINT IF EXISTS correspondences_pkey;
ALTER TABLE IF EXISTS public.thoth_cards ALTER COLUMN card_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.tarot_sessions ALTER COLUMN session_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.spread_pulls ALTER COLUMN spread_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.spread_position_geometry ALTER COLUMN position_id DROP DEFAULT;
ALTER TABLE IF EXISTS public.session_card_pulls ALTER COLUMN pull_id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.thoth_cards_card_id_seq;
DROP TABLE IF EXISTS public.thoth_cards;
DROP SEQUENCE IF EXISTS public.tarot_sessions_session_id_seq;
DROP TABLE IF EXISTS public.tarot_sessions;
DROP SEQUENCE IF EXISTS public.spread_pulls_spread_id_seq;
DROP TABLE IF EXISTS public.spread_pulls;
DROP SEQUENCE IF EXISTS public.spread_position_geometry_position_id_seq;
DROP TABLE IF EXISTS public.spread_position_geometry;
DROP SEQUENCE IF EXISTS public.session_card_pulls_pull_id_seq;
DROP TABLE IF EXISTS public.session_card_pulls;
DROP TABLE IF EXISTS public.correspondences;
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: correspondences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.correspondences (
    key_scale integer NOT NULL,
    name character varying(50) NOT NULL,
    hebrew_letter text,
    element_or_planet_or_sign character varying(30),
    king_scale_color character varying(50),
    attributions jsonb,
    hebrew_letter_french character varying(10) DEFAULT 'N/A'::character varying,
    path_or_sephira_french character varying(50),
    attribution_french character varying(100),
    spatial_type character varying(20),
    spatial_dimension character varying(50),
    platonic_solid character varying(30),
    solid_faces integer,
    solid_vertices integer,
    dual_solid character varying(30),
    topological_role character varying(50),
    french_path integer
);



--
-- Name: session_card_pulls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.session_card_pulls (
    pull_id integer NOT NULL,
    spread_id integer,
    card_id integer,
    position_index integer NOT NULL,
    is_dignified boolean DEFAULT true,
    notes text,
    session_id integer
);



--
-- Name: session_card_pulls_pull_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.session_card_pulls_pull_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: session_card_pulls_pull_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.session_card_pulls_pull_id_seq OWNED BY public.session_card_pulls.pull_id;


--
-- Name: spread_position_geometry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.spread_position_geometry (
    position_id integer NOT NULL,
    spread_key character varying(10) NOT NULL,
    position_index integer NOT NULL,
    position_name character varying(100) NOT NULL,
    pos_x double precision NOT NULL,
    pos_y double precision NOT NULL,
    pos_z double precision DEFAULT 0.0,
    polar_angle_deg double precision
);



--
-- Name: spread_position_geometry_position_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.spread_position_geometry_position_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: spread_position_geometry_position_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.spread_position_geometry_position_id_seq OWNED BY public.spread_position_geometry.position_id;


--
-- Name: spread_pulls; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.spread_pulls (
    spread_id integer NOT NULL,
    session_id integer,
    spread_name character varying(100) NOT NULL,
    pull_order integer NOT NULL
);



--
-- Name: spread_pulls_spread_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.spread_pulls_spread_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: spread_pulls_spread_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.spread_pulls_spread_id_seq OWNED BY public.spread_pulls.spread_id;


--
-- Name: tarot_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tarot_sessions (
    session_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    operation_type character varying(100) NOT NULL,
    significator character varying(100),
    notes text,
    report_settings jsonb
);



--
-- Name: tarot_sessions_session_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tarot_sessions_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: tarot_sessions_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tarot_sessions_session_id_seq OWNED BY public.tarot_sessions.session_id;


--
-- Name: thoth_cards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.thoth_cards (
    card_id integer NOT NULL,
    title character varying(100) NOT NULL,
    arcana_type character varying(20) NOT NULL,
    suit character varying(20),
    number_or_rank character varying(20),
    key_scale integer,
    description text,
    french_number integer,
    attribution character varying(100)
);



--
-- Name: thoth_cards_card_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.thoth_cards_card_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: thoth_cards_card_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.thoth_cards_card_id_seq OWNED BY public.thoth_cards.card_id;


--
-- Name: session_card_pulls pull_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_card_pulls ALTER COLUMN pull_id SET DEFAULT nextval('public.session_card_pulls_pull_id_seq'::regclass);


--
-- Name: spread_position_geometry position_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spread_position_geometry ALTER COLUMN position_id SET DEFAULT nextval('public.spread_position_geometry_position_id_seq'::regclass);


--
-- Name: spread_pulls spread_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spread_pulls ALTER COLUMN spread_id SET DEFAULT nextval('public.spread_pulls_spread_id_seq'::regclass);


--
-- Name: tarot_sessions session_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarot_sessions ALTER COLUMN session_id SET DEFAULT nextval('public.tarot_sessions_session_id_seq'::regclass);


--
-- Name: thoth_cards card_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thoth_cards ALTER COLUMN card_id SET DEFAULT nextval('public.thoth_cards_card_id_seq'::regclass);


--
-- Data for Name: correspondences; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.correspondences (key_scale, name, hebrew_letter, element_or_planet_or_sign, king_scale_color, attributions, hebrew_letter_french, path_or_sephira_french, attribution_french, spatial_type, spatial_dimension, platonic_solid, solid_faces, solid_vertices, dual_solid, topological_role, french_path) FROM stdin;
6	Beauty	תִּפְאֶרֶת (Tiphareth)	🜁	Clear pink rose	{"plants": "Acacia, Bay, Laurel, Vine [[Oak, Gorse, Ash, Aswata]]", "animals": "Phœnix, Lion, Child [[Spider, Pelican]]", "perfumes": "Olibanum", "greek_gods": "Ikarus, Apollo, Adonis [[Dionysis, Bacchus]]", "roman_gods": "Apollo [[Bacchus, Aurora]]", "tree_of_life": "4th Plane - Middle Pillar", "egyptian_gods": "Asar, Ra [[On, Hrumachis]]", "hindu_deities": "Vishu-Hari-Krischna-Rama", "mineral_drugs": "...", "christian_lore": "God the Son (Maker of fine Weather)", "king_scale_hex": "#FFE1FF", "magical_powers": "The Vision of the Harmony of Things (also the Mysteries of the Crucifixion), [[Beatific Vision]]", "mystic_numbers": "21", "magical_weapons": "The Lamen or Rosy Cross", "precious_stones": "Topaz, Yellow Diamond", "queen_scale_hex": "#FFD700", "vegetable_drugs": "Stramonium, Alcohol, Digitalis, Coffee", "magical_formulae": "ABRAHADABRA. IAO: INRI", "system_of_taoism": "Li", "emperor_scale_hex": "#FF8C69", "empress_scale_hex": "#FFC200", "scandinavian_gods": "...", "tarot_attribution": "The 4 Sixes - Emperor or Princes", "the_perfected_man": "The Breast (Mighty Terrible One)", "queen_scale_colors": "Yellow (gold)", "buddhist_meditations": "The Gods", "emperor_scale_colors": "Rich salmon", "empress_scale_colors": "Gold amber", "hindu_buddhist_results": "Vishvarupa-darshana", "practical_egyptian_gods": "Ra", "paths_of_sepher_yetzirah": "Beauty of the Mediating Influence", "lineal_figures_and_geomancy": "...", "figures_related_to_pure_number": "Calvary Cross, Truncated Pyramid, Cube"}	Vav (ו)	Path 16 (Chokmah-Chesed)	Gemini	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	16
0	Limitless LVX - No Limit - Nothing	Ain (אין) - Ain Soph (אין סוף) - Ain Soph Aur (אין סוף אור)	...	...	{"plants": "[[Lotus, Rose]]", "animals": "[[Dragon]]", "perfumes": "[[No attribution possible]]", "greek_gods": "Pan", "roman_gods": "...", "tree_of_life": "...", "egyptian_gods": "Harpocrates, Amoun, Nuith [[Nuit and Hadit]]", "hindu_deities": "AUM", "mineral_drugs": "Carbon", "christian_lore": "...", "king_scale_hex": "...", "magical_powers": "The Supreme Attainment [[Vision of No Difference]]", "mystic_numbers": "0", "magical_weapons": "[[No attribution possible]]", "precious_stones": "[[Star Sapphire, Black Diamond]]", "queen_scale_hex": "...", "vegetable_drugs": "...", "magical_formulae": "LASTAL. M . . . . M", "system_of_taoism": "The Tao or Great Extreme of the Yi King", "emperor_scale_hex": "...", "empress_scale_hex": "...", "scandinavian_gods": "...", "tarot_attribution": "...", "the_perfected_man": "The Hair (Nu)", "queen_scale_colors": "...", "buddhist_meditations": "Nothing and Neither P nor p' | Space | Consciousness", "emperor_scale_colors": "...", "empress_scale_colors": "...", "hindu_buddhist_results": "Nerodha-samapatti, Nirvikalpa- samadhi, Shiva darshana", "practical_egyptian_gods": "Heru-pa-Kraath", "paths_of_sepher_yetzirah": "...", "lineal_figures_and_geomancy": "The Circle", "figures_related_to_pure_number": "..."}	Shin (ש)	Path 31 (Hod-Malkuth)	Unnumbered / Primeval Spirit	\N	\N	\N	\N	\N	\N	\N	31
23	Water	מ (Mem)	Cold & Moist 🜄	Deep blue	{"plants": "Lotus, all Water Plants", "animals": "Eagle-Snake-Scorpion (Cherub of Water)", "perfumes": "Onycha, Myrrh", "greek_gods": "Poseidon", "roman_gods": "Neptune [[Rhea]]", "tree_of_life": "5 to 8", "egyptian_gods": "Tum, Ptah, Auramoth (as Water), Asar (as Hanged Man), Hekar, Isis [[Hathor]", "hindu_deities": "Soma [Apas]", "mineral_drugs": "Sulphates", "christian_lore": "John, Jesus as Hanged Man", "king_scale_hex": "#00008B", "magical_powers": "The Great Work, Talismans, Crystal-gazing, & c.", "mystic_numbers": "276", "magical_weapons": "The Cup and Cross of Suffering, the Wine [[Water of Lustration]]", "precious_stones": "Beryl or Aquamarine", "queen_scale_hex": "#2E8B57", "vegetable_drugs": "Caseara, all purges", "magical_formulae": "...", "system_of_taoism": "Tui", "emperor_scale_hex": "#000080", "empress_scale_hex": "#E6E6FA", "scandinavian_gods": "...", "tarot_attribution": "The Hanged Man - Cups - Queens", "the_perfected_man": "The Belly and Back (Sekhet)", "queen_scale_colors": "Sea-green", "buddhist_meditations": "Water", "emperor_scale_colors": "Blue black", "empress_scale_colors": "White flecked purple", "hindu_buddhist_results": "Apo-Bhawana", "practical_egyptian_gods": "Ieqhourey (To revisit)", "paths_of_sepher_yetzirah": "Stable Water", "lineal_figures_and_geomancy": "Those of 🜄y Triplicity", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Mother_Axis	Horizontal Axis (Width/Breadth)	Icosahedron	20	12	Dodecahedron	Receptive Matrix (Fluid Volume)	\N
28	Fish-hook	צ (Tzaddi)	Saturn - 🜁 - Mercury	Violet	{"plants": "[Olive], Cocoanut", "animals": "Man or Eagle (Cherub of Air), Peacock", "perfumes": "Galbanum", "greek_gods": "[[Athena]] Ganymede", "roman_gods": "Juno [[Æolus]]", "tree_of_life": "7 to 9", "egyptian_gods": "Ahepi, Aroueris", "hindu_deities": "[[The Maruts]]", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#EE82EE", "magical_powers": "Astrology", "mystic_numbers": "406", "magical_weapons": "The Censer or Aspergillus", "precious_stones": "Artificial Glass [[Chalcedony]]", "queen_scale_hex": "#87CEEB", "vegetable_drugs": "All diuretics", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#F5F0FF", "scandinavian_gods": "...", "tarot_attribution": "The Star", "the_perfected_man": "The Reins (Lords of Kereba)", "queen_scale_colors": "Sky blue", "buddhist_meditations": "Purple Corpse", "emperor_scale_colors": "Scarlet, flecked gold", "empress_scale_colors": "White tinged purple", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Nuit", "paths_of_sepher_yetzirah": "Natural Fish-hook", "lineal_figures_and_geomancy": "Tristitia*", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Simple_Edge	Upper-South Edge	Octahedron	8	6	Hexahedron (Cube)	Dynamic Axis (Mediating Air)	\N
20	Hand	י (Yod)	Venus - 🜃 - Moon	Green, yellowish	{"plants": "Snowdrop, Lily, Narcissus [[Mistletoe]]", "animals": "Virgin, Anchorite, any solitary person or animal [[Rhinoceros]]", "perfumes": "Narcissus", "greek_gods": "Attis", "roman_gods": "[Attis], Ceres, Adonis [[Vesta, Flora]]", "tree_of_life": "4 to 6", "egyptian_gods": "Isis (as Virgin)", "hindu_deities": "The Hpo girls, the Lord of Yoga", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#ADFF2F", "magical_powers": "Invisibility, Parthenogenesis, Initiation (?)", "mystic_numbers": "210", "magical_weapons": "The Lamp and Wand (Virile Force reserved), the Bread [[Lotus Wand]]", "precious_stones": "Peridot", "queen_scale_hex": "#708090", "vegetable_drugs": "All anaphrodisiacs", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "#556B2F", "empress_scale_hex": "#DDA0DD", "scandinavian_gods": "...", "tarot_attribution": "Hermit", "the_perfected_man": "...", "queen_scale_colors": "Slate grey", "buddhist_meditations": "Bloated Corpse", "emperor_scale_colors": "Deep olive-green", "empress_scale_colors": "Plum colour", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Heru-pa-Kraath", "paths_of_sepher_yetzirah": "Hand of Will", "lineal_figures_and_geomancy": "Conjunctio *", "figures_related_to_pure_number": "..."}	Resh (ר)	Path 30 (Hod-Yesod)	Fire / Spirit	Simple_Edge	South-West Edge	Hexahedron (Cube)	6	8	Octahedron	Crystallized Vessel (Physical Boundary)	30
18	Fence	ח (Cheth)	Mars - 🜄	Amber	{"plants": "Lotus", "animals": "Crab, Turtle, Sphinx [[Whale, all beasts of Transport]]", "perfumes": "Onycha", "greek_gods": "Apollo The Charioteer", "roman_gods": "Mercury [[Lares and Penates]]", "tree_of_life": "3 to 5", "egyptian_gods": "Khephra", "hindu_deities": "[[Krishna]]", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#FFBF00", "magical_powers": "Power of Casting Enchantments", "mystic_numbers": "171", "magical_weapons": "The Furnace [[The Cup or Holy Graal]]", "precious_stones": "Amber", "queen_scale_hex": "#800000", "vegetable_drugs": "Watercress", "magical_formulae": "ABRAHADABRA", "system_of_taoism": "...", "emperor_scale_hex": "#A040A0", "empress_scale_hex": "#3C241B", "scandinavian_gods": "...", "tarot_attribution": "The Chariot", "the_perfected_man": "...", "queen_scale_colors": "Maroon", "buddhist_meditations": "Worm-eaten Corpse", "emperor_scale_colors": "Rich purple", "empress_scale_colors": "Dark greenish brown", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Hormakhu", "paths_of_sepher_yetzirah": "Fence of the House of Influence", "lineal_figures_and_geomancy": "Populus and Via*", "figures_related_to_pure_number": "..."}	Tzaddi (צ)	Path 28 (Netzach-Yesod)	Pisces	Simple_Edge	Lower-East Edge	Icosahedron	20	12	Dodecahedron	Receptive Matrix (Fluid Volume)	28
4	Mercy	חֶסֶד (Chesed)	🜄	Deep violet	{"plants": "Olive, Shamrock [[Opium Poppy]]", "animals": "Unicorn", "perfumes": "Cedar", "greek_gods": "Poseidon [[Zeus]]", "roman_gods": "Jupiter [[Libitina]]", "tree_of_life": "3rd Plane - Right Pillar", "egyptian_gods": "Amoun,Isis[[Hathoor]]", "hindu_deities": "Indra, Brahma", "mineral_drugs": "...", "christian_lore": "God the Rain-Maker, God the Farmer's Friend", "king_scale_hex": "#9400D3", "magical_powers": "The Vision of Love", "mystic_numbers": "10", "magical_weapons": "The Wand, Sceptre, or Crook", "precious_stones": "Amethyst, Sapphire [[Lapis Lazuli]]", "queen_scale_hex": "#0000FF", "vegetable_drugs": "Opium", "magical_formulae": "IHVH", "system_of_taoism": "...", "emperor_scale_hex": "#9932CC", "empress_scale_hex": "#1E90FF", "scandinavian_gods": "Wotan", "tarot_attribution": "The 4 Fours", "the_perfected_man": "The Arms (Neith)", "queen_scale_colors": "Blue", "buddhist_meditations": "Friendliness", "emperor_scale_colors": "Deep purple", "empress_scale_colors": "Deep azure flecked yellow", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Amoun", "paths_of_sepher_yetzirah": "Measuring Cohesive or Receptcular Mercy", "lineal_figures_and_geomancy": "The Solid Figure", "figures_related_to_pure_number": "Tetrahedron or Pyramid, Cross"}	Daleth (ד)	Path 14 (Chokmah-Binah)	Aries	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	14
5	Strength	גְּבוּרָה (Geburah)	🜂	Orange	{"plants": "Oak, Nux Vomica, Nettle [[Hickory]]", "animals": "Basilisk", "perfumes": "Tobacco", "greek_gods": "Ares, Hades", "roman_gods": "Mars", "tree_of_life": "3rd Plane - Left Pillar", "egyptian_gods": "Horus,Nephthys", "hindu_deities": "Vishnu, Varruna-Avatar", "mineral_drugs": "Iron, Sulphur", "christian_lore": "Christ coming to Judge the World", "king_scale_hex": "#FFA500", "magical_powers": "The Vision of Power", "mystic_numbers": "15", "magical_weapons": "The Sword, Spear, Scourge, or Chain", "precious_stones": "Ruby", "queen_scale_hex": "#FF2400", "vegetable_drugs": "Nux Vomica, Nettle [[Cocaine, Atropine]]", "magical_formulae": "AGLA. ALHIM", "system_of_taoism": "...", "emperor_scale_hex": "#FF2400", "empress_scale_hex": "#8B0000", "scandinavian_gods": "Thor", "tarot_attribution": "The 4 Fives", "the_perfected_man": "The Arms (Neith)", "queen_scale_colors": "Scarlet red", "buddhist_meditations": "Death", "emperor_scale_colors": "Bright scarlet", "empress_scale_colors": "Red flecked black", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Horus", "paths_of_sepher_yetzirah": "Radical Strength", "lineal_figures_and_geomancy": "The Tesseract", "figures_related_to_pure_number": "The Rose"}	Heh (ה)	Path 15 (Chokmah-Tiphareth)	Taurus	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	15
8	Splendour	הוֹד (Hod)	🜄	Violet purple	{"plants": "Moly, Anhalonium Lewinii", "animals": "Hermaphrodite, Jackal [[Twin serpents, Monoceros de Astris]]", "perfumes": "Storax", "greek_gods": "Hermes", "roman_gods": "Mercury", "tree_of_life": "5th Plane - Left Pillar", "egyptian_gods": "Anubis", "hindu_deities": "Hanuman", "mineral_drugs": "Mercury", "christian_lore": "God the Holy Ghost, God the Healer of Plagues", "king_scale_hex": "#A020F0", "magical_powers": "The Vision of Splendour [Ezekiel]", "mystic_numbers": "36", "magical_weapons": "The Names and Versicles and Apron", "precious_stones": "Opal, especially Fire Opal", "queen_scale_hex": "#FFA500", "vegetable_drugs": "Anhalonium Lewinii [[Cannabis Indica]]", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "#330066", "empress_scale_hex": "#DAA520", "scandinavian_gods": "Odin, Loki", "tarot_attribution": "The 4 Eights", "the_perfected_man": "The Reins (Lords of Kereba) - The Hips and Legs (Nuit)", "queen_scale_colors": "Orange", "buddhist_meditations": "Dhamma", "emperor_scale_colors": "Very dark purple", "empress_scale_colors": "Yellow-brown flecked white", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Thoth", "paths_of_sepher_yetzirah": "Absolute (Perfect) Splendour", "lineal_figures_and_geomancy": "...", "figures_related_to_pure_number": "..."}	Cheth (ח)	Path 18 (Binah-Geburah)	Justice / Libra	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	18
3	Understanding	בִּינָה (Binah)	Root of 🜄	Crimson	{"plants": "Cypress, Opium Poppy [[Lotus, Lily, Ivy]]", "animals": "Woman [[Bee]]", "perfumes": "Myrrh, Civet", "greek_gods": "Cybele, Demeter, Rhea, Heré, Kronos, Pyché", "roman_gods": "Juno, Cybele, Hecate", "tree_of_life": "2nd Plane - Left Pillar", "egyptian_gods": "Maut,Isis,Nephthy", "hindu_deities": "Bhavani (All Sakti), Prana (Force), Yoni", "mineral_drugs": "Silver", "christian_lore": "The Virgin Mary", "king_scale_hex": "#DC143C", "magical_powers": "The Vision of Sorrow [[Vision of Wonder]]", "mystic_numbers": "6", "magical_weapons": "Yoni, the Outer Robe of Concealment [[The Cup, the Shining Star]]", "precious_stones": "Star Sapphire, Pearl", "queen_scale_hex": "#000000", "vegetable_drugs": "Belladonna, Soma", "magical_formulae": "BABALON. VITRIOL", "system_of_taoism": "Kwan-se-on, The Yin and Khwan", "emperor_scale_hex": "#654321", "empress_scale_hex": "#C4C4C4", "scandinavian_gods": "Frigga", "tarot_attribution": "The 4 Threes - Queens", "the_perfected_man": "The Face (Disk) & The Neck (Asi)", "queen_scale_colors": "Black", "buddhist_meditations": "Compassion", "emperor_scale_colors": "Dark brown", "empress_scale_colors": "Grey flecked pink", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Nephthys", "paths_of_sepher_yetzirah": "Sanctifying Understanding", "lineal_figures_and_geomancy": "The Plane, also the Diamond, Oval, Circle, and other Yoni Symbols", "figures_related_to_pure_number": "The Triangle"}	Gimel (ג)	Path 13 (Kether-Tiphareth)	Venus	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	13
15	Window	ה (Hé)	Sun - 🜂 - Jupiter	Scarlet	{"plants": "Tiger Lily, Geranium [[Olive]]", "animals": "Ram, Owl", "perfumes": "Dragon's Blood", "greek_gods": "Athena", "roman_gods": "Mars, Minerva", "tree_of_life": "2 to 6", "egyptian_gods": "Men Thu", "hindu_deities": "Shiva, Vishnu, Akasa, Lingam", "mineral_drugs": "...", "christian_lore": "The Disciples (but too indefinite)", "king_scale_hex": "#FF2400", "magical_powers": "Power of Consecrating Things", "mystic_numbers": "120", "magical_weapons": "The Horns, Energy, the Burin", "precious_stones": "Ruby", "queen_scale_hex": "#FF0000", "vegetable_drugs": "All cerebral excitants", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#FF4500", "scandinavian_gods": "...", "tarot_attribution": "The Emperor", "the_perfected_man": "...", "queen_scale_colors": "Red", "buddhist_meditations": "Bloody Corpse", "emperor_scale_colors": "New yellow leather", "empress_scale_colors": "Glowing red", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Isis", "paths_of_sepher_yetzirah": "Constituting Window", "lineal_figures_and_geomancy": "Peur*", "figures_related_to_pure_number": "..."}	Samekh (ס)	Path 25 (Tiphareth-Yesod)	Capricorn	Simple_Edge	North-East Edge	Tetrahedron	4	4	Tetrahedron (Self-Dual)	Primary Ignis Vector (Expansion)	25
31	Tooth	ש (Shin)	Hot & Dry 🜂	Glowing orange scarlet	{"plants": "Red Poppy, Hibiscus, Nettle [[all scarlet flowers]]", "animals": "Lion (Cherub of Fire)", "perfumes": "Olibanum, all Fiery Odours", "greek_gods": "Hades", "roman_gods": "Vulcan, Pluto", "tree_of_life": "8 to 10", "egyptian_gods": "Thoum-Aesh-Neith, Mau, Kabeshunt,\\nHorus, Tarpesheth", "hindu_deities": "Surya (Sun)", "mineral_drugs": "Nitrates", "christian_lore": "Mark", "king_scale_hex": "#FF4500", "magical_powers": "Evocation, Pyromancy", "mystic_numbers": "496", "magical_weapons": "The Wand or Lamp, Pyramid of 🜂  [[The Thurible]]", "precious_stones": "Fire Opal", "queen_scale_hex": "#FF4D00", "vegetable_drugs": "...", "magical_formulae": "...", "system_of_taoism": "Kan", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#E34234", "scandinavian_gods": "...", "tarot_attribution": "The Angel or Last Judgement - Wands - Kings or Knights", "the_perfected_man": "The Teeth - The Breast", "queen_scale_colors": "Vermillion", "buddhist_meditations": "Fire", "emperor_scale_colors": "The 7 prismatic colours, the violet being outside", "empress_scale_colors": "Vermillion flecked crimson & emerald", "hindu_buddhist_results": "Agni-Bhawana", "practical_egyptian_gods": "Mau", "paths_of_sepher_yetzirah": "Perpetual Tooth", "lineal_figures_and_geomancy": "Those of 🜂y Triplicity", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Mother_Axis	Longitudinal Axis (Length/Depth)	Tetrahedron	4	4	Tetrahedron (Self-Dual)	Primary Ignis Vector (Expansion)	\N
24	Fish	נ (Nun)	Mars - 🜄	Green blue	{"plants": "Cactus [[Nettle, all poisonous plants]]", "animals": "Scorpio, Beetle, Crayfish or Lobster, Wolf [[all Reptiles, Shark, Crablouse]]", "perfumes": "Siamese Benzoin, Opoponax", "greek_gods": "Ares [[Apollo the Pythean, Thanatos]]", "roman_gods": "Mars [[Mors]]", "tree_of_life": "6 to 7", "egyptian_gods": "Merti goddesses, Typhon, Apep, Khephra", "hindu_deities": "Kundalini [Yama]]", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#006400", "magical_powers": "Necromancy", "mystic_numbers": "300", "magical_weapons": "The Pain of the Obligation [[The Oath]]", "precious_stones": "Snakestone [[Greenish Turquoise]]", "queen_scale_hex": "#964B00", "vegetable_drugs": "...", "magical_formulae": "AUMGN", "system_of_taoism": "...", "emperor_scale_hex": "#C80815", "empress_scale_hex": "#565051", "scandinavian_gods": "...", "tarot_attribution": "Death", "the_perfected_man": "The Belly and Back (Sekhet)", "queen_scale_colors": "Dull brown", "buddhist_meditations": "Skeleton Corpse", "emperor_scale_colors": "Venetian red", "empress_scale_colors": "Livid indigo brown (like a black beetle)", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Hammemit", "paths_of_sepher_yetzirah": "Imaginative Fish", "lineal_figures_and_geomancy": "Rubeus*", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Simple_Edge	Lower-West Edge	Icosahedron	20	12	Dodecahedron	Receptive Matrix (Fluid Volume)	\N
29	Back of head	ק (Qoph)	Mars - 🜄	Crimson (ultra violet)	{"plants": "Unicellular Organisms, Opium [[Mangrove]]", "animals": "Fish, Dolphin [[Beetle, Dog, Jackal]]", "perfumes": "Ambergris [[Menstrual Fluid]]", "greek_gods": "Poseidon [[Hermes Psychopompus]]", "roman_gods": "Neptune", "tree_of_life": "7 to 10", "egyptian_gods": "Khephra (as Scarab in Tarot Trump)", "hindu_deities": "Vishnu (Matsya Avatar)", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#8A2BE2", "magical_powers": "Bewitchments, Casting Illusions", "mystic_numbers": "435", "magical_weapons": "The Twilight of the Place and Magic Mirror", "precious_stones": "Pearl", "queen_scale_hex": "#CCCCCC", "vegetable_drugs": " All narcotics", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "#000080", "empress_scale_hex": "#AAADB2", "scandinavian_gods": "...", "tarot_attribution": "The Moon", "the_perfected_man": "...", "queen_scale_colors": "Buff, flecked silver-White", "buddhist_meditations": "Conduct", "emperor_scale_colors": "Blue black", "empress_scale_colors": "Stone colour", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Anubi", "paths_of_sepher_yetzirah": "Corporeal Back of head", "lineal_figures_and_geomancy": "Laetitia*", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Simple_Edge	Lower-South Edge	Icosahedron	20	12	Dodecahedron	Receptive Matrix (Fluid Volume)	\N
7	Victory	נֵצַח (Netzach)	🜂	Amber	{"plants": "Rose [[Laurel]]", "animals": "Iynx [[Raven, all carrion birds]]", "perfumes": "Benzoin, Rose, Red Sandal", "greek_gods": "Aphrodite, Nike", "roman_gods": "Venus", "tree_of_life": "5th Plane - Right Pillar", "egyptian_gods": "Hathoor", "hindu_deities": "[[Bhavani, etc.]]", "mineral_drugs": "Arsenic", "christian_lore": "Messiah, Lord of Hosts", "king_scale_hex": "#FFBF00", "magical_powers": "The Vision of Beauty Triumphant", "mystic_numbers": "28", "magical_weapons": "The Lamp and Girdle", "precious_stones": "Emerald", "queen_scale_hex": "#50C878", "vegetable_drugs": "Damiana, Cannabis Indica [[Anhalonium]]", "magical_formulae": "ARARITA", "system_of_taoism": "...", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#808000", "scandinavian_gods": "Freya", "tarot_attribution": "The 4 Sevens", "the_perfected_man": "The Reins (Lords of Kereba) - The Hips and Legs (Nuit)", "queen_scale_colors": "Emerald", "buddhist_meditations": "Analysis into 4 Elements", "emperor_scale_colors": "Bright yellow green Red-russet", "empress_scale_colors": "Olive flecked gold", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Hathoor", "paths_of_sepher_yetzirah": "Hidden (Occult) Victory", "lineal_figures_and_geomancy": "...", "figures_related_to_pure_number": "A Rose (7x7), Candlestick"}	Zain (ז)	Path 17 (Binah-Tiphareth)	Cancer	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	17
17	Sword	ז (Zain)	Saturn - 🜁 - Mercury	Orange	{"plants": "Hybrids, Orchids", "animals": "Magpie, hybrids [[Parrot, Zebra, Penguin]]", "perfumes": "Wormwood", "greek_gods": "Castor and Pollux, Apollo the Diviner, Eros", "roman_gods": "Castor and Pollux, [Janus] [[Hymen]]", "tree_of_life": "3 to 6", "egyptian_gods": "Twin Deities, Rekht, Merti [[Heru-Ra-Ha]]", "hindu_deities": "Various twin and hybrid Deities", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#FFA500", "magical_powers": "Power of being in two or more places at one time, and of Prophecy", "mystic_numbers": "153", "magical_weapons": "The Tripod", "precious_stones": "Alexandrite, Tourmaline, Iceland Spar", "queen_scale_hex": "#FBAED2", "vegetable_drugs": "Ergot and ecbolics", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#9B6E8A", "scandinavian_gods": "...", "tarot_attribution": "The Lovers", "the_perfected_man": "...", "queen_scale_colors": "Pale Mauve", "buddhist_meditations": "White", "emperor_scale_colors": "Grey Green grey", "empress_scale_colors": "Reddish grey inclined to mauve", "hindu_buddhist_results": "...", "practical_egyptian_gods": "The twin Merti ", "paths_of_sepher_yetzirah": "Disposing One Sword", "lineal_figures_and_geomancy": "Albus*", "figures_related_to_pure_number": "Swastika"}	Peh (פ)	Path 27 (Netzach-Hod)	Aquarius	Simple_Edge	Upper-East Edge	Octahedron	8	6	Hexahedron (Cube)	Dynamic Axis (Mediating Air)	27
32	Cross	ת (Tau)	Saturn - 🜃	Indigo	{"plants": "Ash, Cypress, Hellebore, Yew, Nightshade [[Elm]]", "animals": "Crocodile", "perfumes": "Assafœtida, Scammony, Indigo, Sulphur (all Evil Odours)", "greek_gods": "[Athena]", "roman_gods": "Saturn [[Terminus, Astræa]]", "tree_of_life": "9 to 10", "egyptian_gods": "Sebek,Mako", "hindu_deities": "Brahma, Indra", "mineral_drugs": "Lead", "christian_lore": "Ephesus", "king_scale_hex": "#4B0082", "magical_powers": "Works of Malediction and Death", "mystic_numbers": "528", "magical_weapons": "A Sickle", "precious_stones": "Onyx", "queen_scale_hex": "#000000", "vegetable_drugs": "...", "magical_formulae": "...", "system_of_taoism": "Khan", "emperor_scale_hex": "...", "empress_scale_hex": "#00008B", "scandinavian_gods": "...", "tarot_attribution": "The Universe", "the_perfected_man": "The Right Earh (Aput)", "queen_scale_colors": "Black", "buddhist_meditations": "Quiescence", "emperor_scale_colors": "...", "empress_scale_colors": "Black rayed blue", "hindu_buddhist_results": "...", "practical_egyptian_gods": "...", "paths_of_sepher_yetzirah": "Administrative Tau (as Egyptian)", "lineal_figures_and_geomancy": "Triangle", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Double_Direction	Center Core (Holy Temple)	Hexahedron (Cube)	6	8	Octahedron	Crystallized Vessel (Physical Boundary)	\N
12	House	ב (Beth)	Mercury	Yellow	{"plants": "Vervain, Herb Mercury, Major-lane, Palm [[Lime or Linden]]", "animals": "Swallow, Ibis, Ape [[Twin Serpents, fish, hybrids]]", "perfumes": "Mastic, White Sandal [[Nutmeg]], Mace, Storax, all Fugitive Odors", "greek_gods": "Hermes", "roman_gods": "Mercury", "tree_of_life": "1 to 3", "egyptian_gods": "ThothandCynocephalus", "hindu_deities": "Hanuman, Vishnu (Parasa-Rama)", "mineral_drugs": "Mercury", "christian_lore": "Sardis", "king_scale_hex": "#FFFF00", "magical_powers": "Miracles of Healing, Gift of Tongues, Knowledge of Sciences", "mystic_numbers": "78", "magical_weapons": "The Wand or Caduceus", "precious_stones": "Opal, Agate", "queen_scale_hex": "#800080", "vegetable_drugs": "All cerebral excitants", "magical_formulae": "...", "system_of_taoism": "Sun", "emperor_scale_hex": "#00FF7F", "empress_scale_hex": "#8A2BE2", "scandinavian_gods": "...", "tarot_attribution": "The Juggler", "the_perfected_man": "The Lips (Anpu)", "queen_scale_colors": "Purple", "buddhist_meditations": "Yellow", "emperor_scale_colors": "Early spring green", "empress_scale_colors": "Indigo rayed violet", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Thoth", "paths_of_sepher_yetzirah": "House of Transparency", "lineal_figures_and_geomancy": "Octagram", "figures_related_to_pure_number": "Calvary Cross "}	Lamed (ל)	Path 22 (Geburah-Tiphareth)	Water	Double_Direction	Up (Zenith)	Dodecahedron	12	20	Icosahedron	Planetary Celestial Face	22
13	Camel	ג (Gimel)	Moon	Blue	{"plants": "Almond, Mugwort, Hazel (as =), Moonwort, Ranunculus [[Alder, Pomegranate]]", "animals": "Dog [[Stork, Camel]]", "perfumes": "Menstrual Blood, Camphor, Aloes, all Sweet Virginal Odours", "greek_gods": "Artemis, Hekate", "roman_gods": "Diana (as Water) [[Terminus, Jupiter]]", "tree_of_life": "1 to 6", "egyptian_gods": "Chomse", "hindu_deities": "Chandra (as Water)", "mineral_drugs": "...", "christian_lore": "Laodicea", "king_scale_hex": "#0000FF", "magical_powers": "The White Tincture, Clairvoyance, Divination by Dreams", "mystic_numbers": "91", "magical_weapons": "Bow and Arrow", "precious_stones": "Moonstone, Pearl, Crystal", "queen_scale_hex": "#C0C0C0", "vegetable_drugs": "Jupiter, Pennyroyal, & all emmenogogues", "magical_formulae": "ALIM", "system_of_taoism": "Kan and Khwan", "emperor_scale_hex": "#E25822", "empress_scale_hex": "#A6CAF0", "scandinavian_gods": "...", "tarot_attribution": "The High Priestess", "the_perfected_man": "The Left Eye (Hathor)", "queen_scale_colors": "Silver", "buddhist_meditations": "Loathsomeness of Good", "emperor_scale_colors": "Brilliant flame", "empress_scale_colors": "Silver rayed sky-blue", "hindu_buddhist_results": "Vision of Chandra", "practical_egyptian_gods": "Chomse", "paths_of_sepher_yetzirah": "Uniting Camel", "lineal_figures_and_geomancy": "Enneagram", "figures_related_to_pure_number": "Greek Cross (Plane), Table of Shew-bread"}	Mem (מ)	Path 23 (Geburah-Hod)	Scorpio	Double_Direction	Down (Nadir)	Dodecahedron	12	20	Icosahedron	Planetary Celestial Face	23
27	Mouth	פ (Pé)	Mars	Scarlet	{"plants": "Absinthe, Rue", "animals": "Horse, Bear, Wolf [[Boar]]", "perfumes": "Pepper, Dragonís Blood, all Hot Pungent Odours", "greek_gods": "Ares [[Athena]]", "roman_gods": "Mars", "tree_of_life": "7 to 8", "egyptian_gods": "Horus", "hindu_deities": "[[Krishna]]", "mineral_drugs": "...", "christian_lore": "Pergamos", "king_scale_hex": "#FF2400", "magical_powers": "Works of Wrath and Vengeance", "mystic_numbers": "378", "magical_weapons": "The Sword", "precious_stones": "Ruby, any red stone", "queen_scale_hex": "#FF0000", "vegetable_drugs": "...", "magical_formulae": "...", "system_of_taoism": "Kan", "emperor_scale_hex": "#FFBF00", "empress_scale_hex": "#FF4500", "scandinavian_gods": "Tuisco", "tarot_attribution": "The House of God", "the_perfected_man": "The Right Nostril (Khenti-Khas)", "queen_scale_colors": "Red", "buddhist_meditations": "Blood-red", "emperor_scale_colors": "Rich amber", "empress_scale_colors": "Bright red rayed azure or orange", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Mentu", "paths_of_sepher_yetzirah": "Exciting Mouth", "lineal_figures_and_geomancy": "Pentagram", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Double_Direction	North	Dodecahedron	12	20	Icosahedron	Planetary Celestial Face	\N
22	Ox Goad	ל (Lamed)	Saturn - 🜁 - Mercury	Emerald green	{"plants": "Aloe", "animals": "Elephant [[Spider]]", "perfumes": "Galbanum", "greek_gods": "Themis, Minos, Aecus and Rhadamanthus", "roman_gods": "Vulcan [[Venus, Nemesis]]", "tree_of_life": "5 to 6", "egyptian_gods": "Ma", "hindu_deities": "Yama", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#00C957", "magical_powers": "Works of Justice and Equilibrium", "mystic_numbers": "253", "magical_weapons": "The Cross of Equilibrium", "precious_stones": "Emerald", "queen_scale_hex": "#0000FF", "vegetable_drugs": "Tobacco", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "#008000", "empress_scale_hex": "#98FB98", "scandinavian_gods": "...", "tarot_attribution": "Justice", "the_perfected_man": "...", "queen_scale_colors": "Blue", "buddhist_meditations": "Hacked in Pieces Corpse", "emperor_scale_colors": "Green", "empress_scale_colors": "Pale green", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Maat", "paths_of_sepher_yetzirah": "Faithful Ox Goad", "lineal_figures_and_geomancy": "Puella", "figures_related_to_pure_number": "Greek Cross Solid, the Rose (3+7+12)"}	N/A	\N	\N	Simple_Edge	Upper-West Edge	Octahedron	8	6	Hexahedron (Cube)	Dynamic Axis (Mediating Air)	\N
30	Head	ר (Resh)	Sun	Orange	{"plants": "Sunflower, Laural, Heliotrop [[Nut, Galangal]]", "animals": "Lion, Sparrowhawk [[Leopard]]", "perfumes": "Olibanum, Cinnamon, all Glorious Odours", "greek_gods": "Helios, Apollo", "roman_gods": "Apollo [[Ops]]", "tree_of_life": "8 to 9", "egyptian_gods": "Ra", "hindu_deities": "Agni [Tejas], Yama [Last Judgement]", "mineral_drugs": "...", "christian_lore": "Smyrna", "king_scale_hex": "#FFA500", "magical_powers": "The Red Tincture, Power of Acquiring Wealth", "mystic_numbers": "465", "magical_weapons": "The Lamen or Bow and Arrow", "precious_stones": "Crysolith", "queen_scale_hex": "#FFD700", "vegetable_drugs": "Alcohol", "magical_formulae": "IAO : INRI", "system_of_taoism": "Li and Khien", "emperor_scale_hex": "#654321", "empress_scale_hex": "#FFBF00", "scandinavian_gods": "...", "tarot_attribution": "The Sun", "the_perfected_man": "The Right Eye (Hathor)", "queen_scale_colors": "Gold Yellow", "buddhist_meditations": "Light", "emperor_scale_colors": "Dark brown", "empress_scale_colors": "Amber rayed red", "hindu_buddhist_results": "Vision of Surya", "practical_egyptian_gods": "Ra", "paths_of_sepher_yetzirah": "Collecting Head", "lineal_figures_and_geomancy": "Hexagram", "figures_related_to_pure_number": "..."}	N/A	\N	\N	Double_Direction	South	Dodecahedron	12	20	Icosahedron	Planetary Celestial Face	\N
2	Wisdom	חָכְמָה (Chokmah)	Root of 🜂	Pure soft blue	{"plants": "Amaranth [[Mistletoe, Bo or Pipal Tree]]", "animals": "Man ", "perfumes": "Musk", "greek_gods": "Athena, Uranus", "roman_gods": "Janus [[Mercury]]", "tree_of_life": "2nd Plane - Right Pillar", "egyptian_gods": "moun, Thoth, Nuith [Zodiac]", "hindu_deities": "Shiva, Vishnu, Akasa, Lingam", "mineral_drugs": "Phosphorus", "christian_lore": "God the Fater, who guides Parliament", "king_scale_hex": "#87CEEB", "magical_powers": "The Vision of God face to face [[Vision of Antinomies]]", "mystic_numbers": "3", "magical_weapons": "Lingam, the Inner Robe of Glory [[The Word]]", "precious_stones": "Star Ruby, Turquoise", "queen_scale_hex": "#808080", "vegetable_drugs": "Hashish [[Cocaine]]", "magical_formulae": "VIAOV", "system_of_taoism": "The Yang and Khien", "emperor_scale_hex": "#8DA399", "empress_scale_hex": "#FFFFFF", "scandinavian_gods": "Odin", "tarot_attribution": "The 4 Twos - Kings / Knights", "the_perfected_man": "The Face (Disk) & The Neck (Asi)", "queen_scale_colors": "Grey", "buddhist_meditations": "Joy", "emperor_scale_colors": "Blue pearl grey, like mother-of pearl", "empress_scale_colors": "White, flecked red, blue, and yellow", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Isis (as Wisdom)", "paths_of_sepher_yetzirah": "Illuminating Wisdom", "lineal_figures_and_geomancy": "The Line, also the Cross", "figures_related_to_pure_number": "The Cross"}	Beth (ב)	Path 12 (Kether-Binah)	Mercury	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	12
9	Foundation	יְסוֹד (Yesod)	🜁	Indigo	{"plants": "[Banyan], Mandrake, Damiana [[Ginseng, Yohimba]]", "animals": "Elephant [[Tortoise, Toad]]", "perfumes": "Jasmine, Jinseng, all Odoriferous Roots", "greek_gods": "Zeus (as Air), Diana of Epheus, Eros", "roman_gods": "Diana (as Water) [[Terminus, Jupiter]]", "tree_of_life": "6th Plane - Middle Pillar", "egyptian_gods": "Shu [[Hermanubis, all exclusively phallic\\nGods]]", "hindu_deities": "Ganesha, Vishnu (Kurm Avatar)", "mineral_drugs": "Lead", "christian_lore": "God the Holy Ghost (as Incubus)", "king_scale_hex": "#4B0082", "magical_powers": "The Vision of the Machinery of the Universe", "mystic_numbers": "45", "magical_weapons": "The Perfumes and Sandals, The Altar", "precious_stones": "Quartz", "queen_scale_hex": "#EE82EE", "vegetable_drugs": "Orchid Root", "magical_formulae": "ALIM", "system_of_taoism": "...", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#E4D00A", "scandinavian_gods": "...", "tarot_attribution": "The 4 Nines", "the_perfected_man": "The Phallus and Vulva. The Spine", "queen_scale_colors": "Violet", "buddhist_meditations": "Sangha & The Body", "emperor_scale_colors": "As Queen scale, but flecked with gold", "empress_scale_colors": "Citrine flecked azure", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Shu", "paths_of_sepher_yetzirah": "Pure (Clear) Foundation", "lineal_figures_and_geomancy": "...", "figures_related_to_pure_number": "..."}	Teth (ט)	Path 19 (Chesed-Geburah)	Virgo	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	19
10	Kingdom	מַלְכוּת (Malkuth)	🜃	Yellow	{"plants": "Willow, Lily, Ivy [[Pomegranate, all cereals]]", "animals": "Sphinx", "perfumes": "Dittany of Crete", "greek_gods": "Persephone, Adonis, Psyche", "roman_gods": "Ceres", "tree_of_life": "7th Plane - Middle Pillar", "egyptian_gods": "Seb. Lower (i.e. unwedded) Isis and Neph-\\nthys. [[Sphinx as synthesis of Elements]]", "hindu_deities": "Lakshmi [Kundalini]", "mineral_drugs": "Mag. Sulph.", "christian_lore": "Ecclesia Xsti, the Virgin Mary", "king_scale_hex": "#FFFF00", "magical_powers": "The Vision of the Holy Guardian Angel or of Adonai", "mystic_numbers": "55", "magical_weapons": "The Magical Circle and Triangle", "precious_stones": "Rock Crystal", "queen_scale_hex": "#E4D00A", "vegetable_drugs": "Corn", "magical_formulae": "VITRIOL", "system_of_taoism": "Khan", "emperor_scale_hex": "#669999", "empress_scale_hex": "#F8D568", "scandinavian_gods": "...", "tarot_attribution": "The 4 Tens - Empresses or Princesses", "the_perfected_man": "The Buttocks and Anus (Eye of Hoor)", "queen_scale_colors": "Citrine", "buddhist_meditations": "Sangha & The Body", "emperor_scale_colors": "Blue emerald green Grey", "empress_scale_colors": "Black rayed yellow", "hindu_buddhist_results": "Vision of the “Higher Self,” the various Dhyanas or Jhanas", "practical_egyptian_gods": "Osiris", "paths_of_sepher_yetzirah": "Resplendent Kingdom", "lineal_figures_and_geomancy": "...", "figures_related_to_pure_number": "Altar (Double Cube), Calvary Cross"}	Yod (י)	Path 20 (Chesed-Tiphareth)	Jupiter	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	20
19	Serpent	ט (Teth)	Sun - 🜂 - Jupiter	Yellow, greenish	{"plants": "Sunflower", "animals": "Lion (Cherub of B) [[Cat, Tiger, Serpent, Woman]]", "perfumes": "Olibanum", "greek_gods": "Demeter", "roman_gods": "Venus (Repressing Fire of Vulcan)", "tree_of_life": "4 to 5", "egyptian_gods": "Ra-Hoor-Khuit,Pasht,Sekhet,Mau", "hindu_deities": "Vishnu (Nara-Singh Avatar)", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#ADFF2F", "magical_powers": "Power of Training Wild Beasts", "mystic_numbers": "190", "magical_weapons": "The Discipline (Preliminary) [[Phoenix Wand]]", "precious_stones": "Cat's Eye", "queen_scale_hex": "#9932CC", "vegetable_drugs": "All carminatives and tonics", "magical_formulae": "ΤΟ ΜΕΓΑ ΘΗΡΙΟΝ", "system_of_taoism": "...", "emperor_scale_hex": "#006994", "empress_scale_hex": "#FF4500", "scandinavian_gods": "...", "tarot_attribution": "Strength", "the_perfected_man": "The Breast (Mighty Terrible One)", "queen_scale_colors": "Deep purple", "buddhist_meditations": "Gnawed by Wild Beasts Corpse", "emperor_scale_colors": "Deep blue-green", "empress_scale_colors": "Reddish amber", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Horus", "paths_of_sepher_yetzirah": "Serpent of all the Activities of the Spiritual Being", "lineal_figures_and_geomancy": "Fortuna Major and Fortuna Minor*", "figures_related_to_pure_number": "..."}	Qoph (ק)	Path 29 (Netzach-Malkuth)	Sun	Simple_Edge	North-West Edge	Tetrahedron	4	4	Tetrahedron (Self-Dual)	Primary Ignis Vector (Expansion)	29
21	Palm	כ (Kaph)	Jupiter	Violet	{"plants": "Hyssop, Oak, Poplar, Fig [[Arnica, Cedar]]", "animals": "Eagle [[Praying Mantis]]", "perfumes": "Saffron", "greek_gods": "Zeus", "roman_gods": "Jupiter, [Pluto]", "tree_of_life": "4 to 7", "egyptian_gods": "Amoun-Ra", "hindu_deities": "Brahma, Indra", "mineral_drugs": "...", "christian_lore": "Philadelphia", "king_scale_hex": "#EE82EE", "magical_powers": "Power of Acquiring Political and other Ascendency", "mystic_numbers": "231", "magical_weapons": "The Sceptre", "precious_stones": "Amethyst, Lapis Lazuli", "queen_scale_hex": "#0000FF", "vegetable_drugs": "Cocaine", "magical_formulae": "...", "system_of_taoism": "Li", "emperor_scale_hex": "#321414", "empress_scale_hex": "#00FFFF", "scandinavian_gods": "...", "tarot_attribution": "Wheel of Fortune", "the_perfected_man": "The Left Ear (Aput)", "queen_scale_colors": "Blue", "buddhist_meditations": "Liberality", "emperor_scale_colors": "Very dark brown", "empress_scale_colors": "Bright blue rayed yellow", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Amoun-Ra", "paths_of_sepher_yetzirah": "Palm of Conciliation", "lineal_figures_and_geomancy": "Square and Rhombus", "figures_related_to_pure_number": "..."}	Tav (ת)	Path 32 (Yesod-Malkuth)	Saturn / Earth	Double_Direction	West	Dodecahedron	12	20	Icosahedron	Planetary Celestial Face	32
25	Prop	ס (Samekh)	Sun - 🜂 - Jupiter	Blue	{"plants": "Rush", "animals": " Centaur, Horse, Hippogriff, Dog", "perfumes": "Lign-aloes", "greek_gods": "Apollo, Artemis (hunters)", "roman_gods": "Diana (Archer) [[Iris]]", "tree_of_life": "6 to 9", "egyptian_gods": "Nephthys", "hindu_deities": "Vishnu (Horse-Avatar)", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#0000FF", "magical_powers": "Transmutations [[Vision of Universal Peacock]]", "mystic_numbers": "325", "magical_weapons": "The Arrow (swift and straight application of force)", "precious_stones": "Jacinth", "queen_scale_hex": "#FFFF00", "vegetable_drugs": "...", "magical_formulae": "ON", "system_of_taoism": "...", "emperor_scale_hex": "#9370DB", "empress_scale_hex": "#002FA7", "scandinavian_gods": "...", "tarot_attribution": "Temperence", "the_perfected_man": "...", "queen_scale_colors": "Yellow", "buddhist_meditations": "Limited Aperture", "emperor_scale_colors": "Blueish mauve", "empress_scale_colors": "Dark vivid blue", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Arwuerie (To revisit)", "paths_of_sepher_yetzirah": "Prop of Probation (Tentative) One", "lineal_figures_and_geomancy": "Acquisitio*", "figures_related_to_pure_number": "The Rose (5x5)"}	N/A	\N	\N	Simple_Edge	Upper-North Edge	Tetrahedron	4	4	Tetrahedron (Self-Dual)	Primary Ignis Vector (Expansion)	\N
26	Eye	ע (Ayin)	Venus - 🜃 - Moon	Indigo	{"plants": "Indian Hemp, Orchis Root, Thistle [[Yohimba]]", "animals": "Goat, Ass [[Oyster]]", "perfumes": "Musk, Civet ( also ♄ian Perfumes)", "greek_gods": "Pan, Priapus", "roman_gods": "Pan, Vesta, Bacchus", "tree_of_life": "6 to 8", "egyptian_gods": "Khem (Set)", "hindu_deities": "Lingam, Yoni", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#4B0082", "magical_powers": "The Witches' Sabbath so-called, the Evil Eye", "mystic_numbers": "351", "magical_weapons": "The Secret Force, Lamp", "precious_stones": "Black Diamond", "queen_scale_hex": "#000000", "vegetable_drugs": "Orchis [Satyrion]", "magical_formulae": "ON", "system_of_taoism": "...", "emperor_scale_hex": "Not a valid color description", "empress_scale_hex": "#292929", "scandinavian_gods": "...", "tarot_attribution": "The Devil", "the_perfected_man": "The Buttocks and Anus (Eye of Hoor)", "queen_scale_colors": "Black", "buddhist_meditations": "Putrid Corpse", "emperor_scale_colors": "Light translucent pinksh brown", "empress_scale_colors": "Cold dark grey near black", "hindu_buddhist_results": "...", "practical_egyptian_gods": "Set", "paths_of_sepher_yetzirah": "Renovating Eye", "lineal_figures_and_geomancy": "Carcer*", "figures_related_to_pure_number": "Calvary Cross of 10, Solid"}	N/A	\N	\N	Simple_Edge	Lower-North Edge	Hexahedron (Cube)	6	8	Octahedron	Crystallized Vessel (Physical Boundary)	\N
1	Crown	כֶּתֶר (Kether)	Root of 🜁	Brilliance	{"plants": "Almond in Flower [[Banyan]] ", "animals": "God [[Swan, Hawk]] Man", "perfumes": "Ambergris", "greek_gods": "Zeus, Ikarus", "roman_gods": "Jupiter", "tree_of_life": "1st Plane - Middle Pillar", "egyptian_gods": "Ptah, Asar un Nefer, Hadith [[Heru-Ra-Ha]]", "hindu_deities": "Parabrahm [[Shiva, Brahma]]", "mineral_drugs": "Aur. Pot.", "christian_lore": "God the 3 in 1", "king_scale_hex": "#FFFFFF", "magical_powers": "Union with God", "mystic_numbers": "1", "magical_weapons": "Swastika or Fylfot Cross, Crown [[The Lamp]]", "precious_stones": "Diamond", "queen_scale_hex": "#FFFFFF", "vegetable_drugs": "Elixir Vitæ", "magical_formulae": "...", "system_of_taoism": "Shang Ti (also the Tao)", "emperor_scale_hex": "#FFFFFF", "empress_scale_hex": "#FFECB3", "scandinavian_gods": "Wotan", "tarot_attribution": "The 4 Aces", "the_perfected_man": "The Face (Disk) & The Neck (Asi)", "queen_scale_colors": "White brilliance", "buddhist_meditations": "Indifference", "emperor_scale_colors": "White brilliance", "empress_scale_colors": "White flecked gold", "hindu_buddhist_results": "Unity with Brahma, Atma darshana", "practical_egyptian_gods": "Ptah", "paths_of_sepher_yetzirah": "Admirable", "lineal_figures_and_geomancy": "The Point", "figures_related_to_pure_number": "..."}	Aleph (א)	Path 11 (Kether-Chokmah)	Air / Magus Spirit	\N	\N	Dodecahedron	12	20	Icosahedron	Quintessential Core (12 Zodiacal Pentagons)	11
11	Ox	א (Aleph)	Hot & Moist 🜁	Bright pale yellow	{"plants": "Aspen", "animals": "Eagle, Man (Cherub of D) [[Ox]] ", "perfumes": "Galbanum", "greek_gods": "Zeus", "roman_gods": "Jupiter [[Juno, Æolus]]", "tree_of_life": "1 to 2", "egyptian_gods": "Nu [[Hoor-pa-kraat as ATU 0]]", "hindu_deities": "The Maruts [Vayu]", "mineral_drugs": "...", "christian_lore": "Matthew", "king_scale_hex": "#FFFF9D", "magical_powers": "Divination", "mystic_numbers": "66", "magical_weapons": "The Dagger or Fan", "precious_stones": "Topaz", "queen_scale_hex": "#87CEEB", "vegetable_drugs": "Peppermint", "magical_formulae": "...", "system_of_taoism": "Sun", "emperor_scale_hex": "#AECBF0", "empress_scale_hex": "#50C878", "scandinavian_gods": "Valkyries", "tarot_attribution": "The Fool - Swords - Emperors of Princes", "the_perfected_man": "The Breast (Mighty Terrible One)", "queen_scale_colors": "Sky blue", "buddhist_meditations": "Wind", "emperor_scale_colors": "Cold pale blue", "empress_scale_colors": "Emerald flecked gold", "hindu_buddhist_results": "Vaya-Bhawana", "practical_egyptian_gods": "Mout", "paths_of_sepher_yetzirah": "Scintillating Ox", "lineal_figures_and_geomancy": "Those of 🜁y Triplicity", "figures_related_to_pure_number": "..."}	Kaph (כ)	Path 21 (Chesed-Netzach)	Strength / Leo	Mother_Axis	Vertical Axis (Height/Depth)	Octahedron	8	6	Hexahedron (Cube)	Dynamic Axis (Mediating Air)	21
14	Door	ד (Daleth)	Venus	Emerald green	{"plants": "Myrtle, Rose, Clover [[Fig, Peach, Apple]]", "animals": "Sparrow, Dove [[Swan, Sow, birds generally]]", "perfumes": "Sandalwood, Myrtle, all Soft Voluptuous Odours", "greek_gods": "Aphrodite", "roman_gods": "Venus", "tree_of_life": "2 to 3", "egyptian_gods": "Hathor", "hindu_deities": "Lalita (sexual aspect of Sakti)", "mineral_drugs": "...", "christian_lore": "Thyatira", "king_scale_hex": "#00C957", "magical_powers": "Love-philtres", "mystic_numbers": "105", "magical_weapons": "The Girdle", "precious_stones": "Emerald, Turquoise", "queen_scale_hex": "#87CEEB", "vegetable_drugs": "All aphrodisiacs", "magical_formulae": "ΑΓΑΠΗ", "system_of_taoism": "Tui", "emperor_scale_hex": "#58423F", "empress_scale_hex": "#FF69B4", "scandinavian_gods": "Freya", "tarot_attribution": "The Empress", "the_perfected_man": "The Left Nostril (Khenti-Khas)", "queen_scale_colors": "Sky blue", "buddhist_meditations": "Dark Blue", "emperor_scale_colors": "Deep warm olive", "empress_scale_colors": "Bright rose of cerise rayed pale yellow", "hindu_buddhist_results": "Success in Bhaktioga", "practical_egyptian_gods": "Hathoor", "paths_of_sepher_yetzirah": "Illuminating Door", "lineal_figures_and_geomancy": "Heptagram", "figures_related_to_pure_number": "..."}	Nun (נ)	Path 24 (Tiphareth-Netzach)	Sagittarius	Double_Direction	East	Dodecahedron	12	20	Icosahedron	Planetary Celestial Face	24
16	Nail	ו (Vau)	Venus - 🜃 - Moon	Red orange	{"plants": "Mallow [[all giant trees]]", "animals": "Bull (Cherub of E) [[all beasts of Burden]] ", "perfumes": "Storax", "greek_gods": "Here", "roman_gods": "Venus [[Hymen]]", "tree_of_life": "2 to 4", "egyptian_gods": "Asar,Ameshet,Apis", "hindu_deities": "Shiva (Sacred Bull)", "mineral_drugs": "...", "christian_lore": "...", "king_scale_hex": "#FF4500", "magical_powers": "The Secret of Physical Strength", "mystic_numbers": "136", "magical_weapons": "The Labour of Preparation [[The Throne and Altar]]", "precious_stones": "Topaz", "queen_scale_hex": "#4B0082", "vegetable_drugs": "Sugar", "magical_formulae": "...", "system_of_taoism": "...", "emperor_scale_hex": "#D93C30", "empress_scale_hex": "#964B00", "scandinavian_gods": "...", "tarot_attribution": "The Hierophant", "the_perfected_man": "The Shoulders (Ba-Neb-Tattu)", "queen_scale_colors": "Deep indigo", "buddhist_meditations": "Beaten and Scattered Corpse", "emperor_scale_colors": "Rich bright russet", "empress_scale_colors": "Rich brown", "hindu_buddhist_results": "Success in Hathayoga, Asana\\nand Prana-yama", "practical_egyptian_gods": "Osiris", "paths_of_sepher_yetzirah": "Triumphal (Eternal One) Nail", "lineal_figures_and_geomancy": "Amission*", "figures_related_to_pure_number": "..."}	Ayin (ע)	Path 26 (Tiphareth-Hod)	Mars	Simple_Edge	South-East Edge	Hexahedron (Cube)	6	8	Octahedron	Crystallized Vessel (Physical Boundary)	26
\.


--
-- Data for Name: spread_position_geometry; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.spread_position_geometry (position_id, spread_key, position_index, position_name, pos_x, pos_y, pos_z, polar_angle_deg) FROM stdin;
1	6	1	Saturn (Top Apex)	0	1	0	90
2	6	2	Jupiter (Right Top)	0.866	0.5	0	30
3	6	3	Mars (Right Bottom)	0.866	-0.5	0	330
4	6	4	Venus (Bottom Apex)	0	-1	0	270
5	6	5	Mercury (Left Bottom)	-0.866	-0.5	0	210
6	6	6	Sun (Left Top)	-0.866	0.5	0	150
7	6	7	Moon (Center Core)	0	0	0	0
8	10	1	Aries	1	0	0	0
9	10	2	Taurus	0.866	0.5	0	30
10	10	3	Gemini	0.5	0.866	0	60
11	10	4	Cancer	0	1	0	90
12	10	5	Leo	-0.5	0.866	0	120
13	10	6	Virgo	-0.866	0.5	0	150
14	10	7	Libra	-1	0	0	180
15	10	8	Scorpio	-0.866	-0.5	0	210
16	10	9	Sagittarius	-0.5	-0.866	0	240
17	10	10	Capricorn	0	-1	0	270
18	10	11	Aquarius	0.5	-0.866	0	300
19	10	12	Pisces	0.866	-0.5	0	330
\.


--
-- Data for Name: thoth_cards; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.thoth_cards (card_id, title, arcana_type, suit, number_or_rank, key_scale, description, french_number, attribution) FROM stdin;
1	0 - The Fool	Major	\N	0	11	Air. Pure unconditioned potential, Spirit entering creation.	0	Air
2	I - The Magus	Major	\N	I	12	Mercury. Wisdom, communication, action, and illusion.	1	Mercury
3	II - The Priestess	Major	\N	II	13	Moon. Pure intuition, the veil of Isis, raw receptivity.	2	Moon
4	III - The Empress	Major	\N	III	14	Venus. Creative imagination, love, beauty, and embodiment.	3	Venus
5	IV - The Emperor	Major	\N	IV	28	Aries. Authority, structure, governance, and order (Tzaddi).	4	Aries
6	V - The Hierophant	Major	\N	V	16	Taurus. Wisdom, spiritual teaching, and foundational structure.	5	Taurus
7	VI - The Lovers	Major	\N	VI	17	Gemini. Analysis, division, dynamic choice, and intellectual synthesis.	6	Gemini
8	VII - The Chariot	Major	\N	VII	18	Cancer. Triumph, protection, containment, and directed motion.	7	Cancer
9	VIII - Adjustment	Major	\N	VIII	22	Libra. Balance, justice, precision, and equilibrium (Lamed).	8	Libra
10	IX - The Hermit	Major	\N	IX	20	Virgo. Inner light, solitude, introspective analysis, and initiation.	9	Virgo
11	X - Fortune	Major	\N	X	21	Jupiter. Cyclic movement, destiny, and cosmic rhythm.	10	Jupiter
12	XI - Lust	Major	\N	XI	19	Leo. Strength, vitality, passionate engagement, and control (Teth).	11	Leo
13	XII - The Hanged Man	Major	\N	XII	23	Water. Surrender, sacrifice, elemental transformation, and devotion.	12	Water
14	XIII - Death	Major	\N	XIII	24	Scorpio. Putrefaction, essential transformation, and rebirth.	13	Scorpio
15	XIV - Art	Major	\N	XIV	25	Sagittarius. Alchemical integration, synthesis, and balanced combination.	14	Sagittarius
16	XV - The Devil	Major	\N	XV	26	Capricorn. Material bondage, raw creative vigor, and Pan energy.	15	Capricorn
17	XVI - The Tower	Major	\N	XVI	27	Mars. Sudden breakdown, shock, illumination, and shattering of forms.	16	Mars
18	XVII - The Star	Major	\N	XVII	15	Aquarius. Hope, meditation, clear insight, and cosmic influence (Heh).	17	Aquarius
19	XVIII - The Moon	Major	\N	XVIII	29	Pisces. Illusion, threshold crossing, the subconscious, and physical mystery.	18	Pisces
20	XIX - The Sun	Major	\N	XIX	30	Sun. Direct light, clarity, vitality, and unified consciousness.	19	Sun
21	XX - The Aeon	Major	\N	XX	31	Fire/Spirit. Final judgment, shift of eras, and new spiritual awakening.	20	Fire / Spirit
22	XXI - The Universe	Major	\N	XXI	32	Saturn/Earth. Completion, cosmic synthesis, and fully realized manifestation.	21	Saturn / Earth
23	Ace of Wands	Minor	Wands	1	1	Root of Fire. Creative impulse.	\N	Root of the Powers of Fire
24	2 of Wands - Dominion	Minor	Wands	2	2	Chokmah in Fire. Mars in Aries.	\N	Mars in Aries
25	3 of Wands - Virtue	Minor	Wands	3	3	Binah in Fire. Sun in Aries.	\N	Sun in Aries
26	4 of Wands - Completion	Minor	Wands	4	4	Chesed in Fire. Venus in Aries.	\N	Venus in Aries
27	5 of Wands - Strife	Minor	Wands	5	5	Geburah in Fire. Saturn in Leo.	\N	Saturn in Leo
28	6 of Wands - Victory	Minor	Wands	6	6	Tiphareth in Fire. Jupiter in Leo.	\N	Jupiter in Leo
29	7 of Wands - Valour	Minor	Wands	7	7	Netzach in Fire. Mars in Leo.	\N	Mars in Leo
30	8 of Wands - Swiftness	Minor	Wands	8	8	Hod in Fire. Mercury in Sagittarius.	\N	Mercury in Sagittarius
31	9 of Wands - Strength	Minor	Wands	9	9	Yesod in Fire. Moon in Sagittarius.	\N	Moon in Sagittarius
32	10 of Wands - Oppression	Minor	Wands	10	10	Malkuth in Fire. Saturn in Sagittarius.	\N	Saturn in Sagittarius
33	Ace of Cups	Minor	Cups	1	1	Root of Water. Receptive love.	\N	Root of the Powers of Water
34	2 of Cups - Love	Minor	Cups	2	2	Chokmah in Water. Venus in Cancer.	\N	Venus in Cancer
35	3 of Cups - Abundance	Minor	Cups	3	3	Binah in Water. Mercury in Cancer.	\N	Mercury in Cancer
36	4 of Cups - Luxury	Minor	Cups	4	4	Chesed in Water. Moon in Cancer.	\N	Moon in Cancer
37	5 of Cups - Disappointment	Minor	Cups	5	5	Geburah in Water. Mars in Scorpio.	\N	Mars in Scorpio
38	6 of Cups - Pleasure	Minor	Cups	6	6	Tiphareth in Water. Sun in Scorpio.	\N	Sun in Scorpio
39	7 of Cups - Debauch	Minor	Cups	7	7	Netzach in Water. Venus in Scorpio.	\N	Venus in Scorpio
40	8 of Cups - Indolence	Minor	Cups	8	8	Hod in Water. Saturn in Pisces.	\N	Saturn in Pisces
41	9 of Cups - Happiness	Minor	Cups	9	9	Yesod in Water. Jupiter in Pisces.	\N	Jupiter in Pisces
42	10 of Cups - Satiety	Minor	Cups	10	10	Malkuth in Water. Mars in Pisces.	\N	Mars in Pisces
43	Ace of Swords	Minor	Swords	1	1	Root of Air. Pure intellect.	\N	Root of the Powers of Air
44	2 of Swords - Peace	Minor	Swords	2	2	Chokmah in Air. Moon in Libra.	\N	Moon in Libra
45	3 of Swords - Sorrow	Minor	Swords	3	3	Binah in Air. Saturn in Libra.	\N	Saturn in Libra
46	4 of Swords - Truce	Minor	Swords	4	4	Chesed in Air. Jupiter in Libra.	\N	Jupiter in Libra
47	5 of Swords - Defeat	Minor	Swords	5	5	Geburah in Air. Venus in Aquarius.	\N	Venus in Aquarius
48	6 of Swords - Science	Minor	Swords	6	6	Tiphareth in Air. Mercury in Aquarius.	\N	Mercury in Aquarius
49	7 of Swords - Futility	Minor	Swords	7	7	Netzach in Air. Moon in Aquarius.	\N	Moon in Aquarius
50	8 of Swords - Interference	Minor	Swords	8	8	Hod in Air. Jupiter in Gemini.	\N	Jupiter in Gemini
51	9 of Swords - Cruelty	Minor	Swords	9	9	Yesod in Air. Mars in Gemini.	\N	Mars in Gemini
52	10 of Swords - Ruin	Minor	Swords	10	10	Malkuth in Air. Sun in Gemini.	\N	Sun in Gemini
53	Ace of Disks	Minor	Disks	1	1	Root of Earth. Matter and manifestation.	\N	Root of the Powers of Earth
54	2 of Disks - Change	Minor	Disks	2	2	Chokmah in Earth. Jupiter in Capricorn.	\N	Jupiter in Capricorn
55	3 of Disks - Works	Minor	Disks	3	3	Binah in Earth. Mars in Capricorn.	\N	Mars in Capricorn
56	4 of Disks - Power	Minor	Disks	4	4	Chesed in Earth. Sun in Capricorn.	\N	Sun in Capricorn
57	5 of Disks - Worry	Minor	Disks	5	5	Geburah in Earth. Mercury in Taurus.	\N	Mercury in Taurus
58	6 of Disks - Success	Minor	Disks	6	6	Tiphareth in Earth. Moon in Taurus.	\N	Moon in Taurus
59	7 of Disks - Failure	Minor	Disks	7	7	Netzach in Earth. Saturn in Taurus.	\N	Saturn in Taurus
60	8 of Disks - Prudence	Minor	Disks	8	8	Hod in Earth. Sun in Virgo.	\N	Sun in Virgo
61	9 of Disks - Gain	Minor	Disks	9	9	Yesod in Earth. Venus in Virgo.	\N	Venus in Virgo
62	10 of Disks - Wealth	Minor	Disks	10	10	Malkuth in Earth. Mercury in Virgo.	\N	Mercury in Virgo
63	Knight of Wands	Court	Wands	Knight	25	Fire of Fire. Sagittarius attribution.	\N	Fire of Fire - 20° Scorpio to 20° Sagittarius
64	Queen of Wands	Court	Wands	Queen	28	Water of Fire. Aries attribution.	\N	Water of Fire - 20° Pisces to 20° Aries
65	Prince of Wands	Court	Wands	Prince	19	Air of Fire. Leo attribution.	\N	Air of Fire - 20° Cancer to 20° Leo
66	Princess of Wands	Court	Wands	Princess	31	Earth of Fire. Fuel for the fire.	\N	Earth of Fire - Cancer, Leo, Virgo quadrant
67	Knight of Cups	Court	Cups	Knight	29	Fire of Water. Pisces attribution.	\N	Fire of Water - 20° Aquarius to 20° Pisces
68	Queen of Cups	Court	Cups	Queen	18	Water of Water. Pure elemental emotion.	\N	Water of Water - 20° Gemini to 20° Cancer
69	Prince of Cups	Court	Cups	Prince	24	Air of Water. Mentalized sentiment.	\N	Air of Water - 20° Libra to 20° Scorpio
70	Princess of Cups	Court	Cups	Princess	23	Earth of Water. Crystalized feeling.	\N	Earth of Water - Libra, Scorpio, Sagittarius quadrant
71	Knight of Swords	Court	Swords	Knight	17	Fire of Air. Active, analytical drive (Gemini).	\N	Fire of Air - 20° Taurus to 20° Gemini
72	Queen of Swords	Court	Swords	Queen	22	Water of Air. Clear judgment (Libra).	\N	Water of Air - 20° Virgo to 20° Libra
73	Prince of Swords	Court	Swords	Prince	15	Air of Air. Pure intellectual impulse (Aquarius).	\N	Air of Air - 20° Capricorn to 20° Aquarius
74	Princess of Swords	Court	Swords	Princess	11	Earth of Air. Practical analysis.	\N	Earth of Air - Capricorn, Aquarius, Pisces quadrant
75	Knight of Disks	Court	Disks	Knight	20	Fire of Earth. Virgo attribution.	\N	Fire of Earth - 20° Leo to 20° Virgo
76	Queen of Disks	Court	Disks	Queen	26	Water of Earth. Capricorn attribution.	\N	Water of Earth - 20° Sagittarius to 20° Capricorn
77	Prince of Disks	Court	Disks	Prince	16	Air of Earth. Taurus attribution.	\N	Air of Earth - 20° Aries to 20° Taurus
78	Princess of Disks	Court	Disks	Princess	32	Earth of Earth. Physical birth/manifestation.	\N	Earth of Earth - Aries, Taurus, Gemini quadrant
\.


--
-- Name: session_card_pulls_pull_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.session_card_pulls_pull_id_seq', 4, true);


--
-- Name: spread_position_geometry_position_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.spread_position_geometry_position_id_seq', 19, true);


--
-- Name: spread_pulls_spread_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.spread_pulls_spread_id_seq', 1, true);


--
-- Name: tarot_sessions_session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.tarot_sessions_session_id_seq', 1, true);


--
-- Name: thoth_cards_card_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.thoth_cards_card_id_seq', 78, true);


--
-- Name: correspondences correspondences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.correspondences
    ADD CONSTRAINT correspondences_pkey PRIMARY KEY (key_scale);


--
-- Name: session_card_pulls session_card_pulls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_card_pulls
    ADD CONSTRAINT session_card_pulls_pkey PRIMARY KEY (pull_id);


--
-- Name: spread_position_geometry spread_position_geometry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spread_position_geometry
    ADD CONSTRAINT spread_position_geometry_pkey PRIMARY KEY (position_id);


--
-- Name: spread_pulls spread_pulls_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spread_pulls
    ADD CONSTRAINT spread_pulls_pkey PRIMARY KEY (spread_id);


--
-- Name: tarot_sessions tarot_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tarot_sessions
    ADD CONSTRAINT tarot_sessions_pkey PRIMARY KEY (session_id);


--
-- Name: thoth_cards thoth_cards_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thoth_cards
    ADD CONSTRAINT thoth_cards_pkey1 PRIMARY KEY (card_id);


--
-- Name: thoth_cards unique_card_title; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.thoth_cards
    ADD CONSTRAINT unique_card_title UNIQUE (title);


--
-- Name: idx_cards_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cards_fts ON public.thoth_cards USING gin (to_tsvector('english'::regconfig, (((title)::text || ' '::text) || COALESCE(description, ''::text))));


--
-- Name: idx_cards_key_scale; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cards_key_scale ON public.thoth_cards USING btree (key_scale);


--
-- Name: session_card_pulls session_card_pulls_card_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_card_pulls
    ADD CONSTRAINT session_card_pulls_card_id_fkey FOREIGN KEY (card_id) REFERENCES public.thoth_cards(card_id) ON DELETE RESTRICT;


--
-- Name: session_card_pulls session_card_pulls_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_card_pulls
    ADD CONSTRAINT session_card_pulls_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.tarot_sessions(session_id) ON DELETE CASCADE;


--
-- Name: session_card_pulls session_card_pulls_spread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.session_card_pulls
    ADD CONSTRAINT session_card_pulls_spread_id_fkey FOREIGN KEY (spread_id) REFERENCES public.spread_pulls(spread_id) ON DELETE CASCADE;


--
-- Name: spread_pulls spread_pulls_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.spread_pulls
    ADD CONSTRAINT spread_pulls_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.tarot_sessions(session_id) ON DELETE CASCADE;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--



--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: -
--



--
-- PostgreSQL database dump complete
--

\unrestrict TlcpppKLPezyITSwjwz9FNdJjzIqpmcAjeKjG6oYwPiHoUfzo7TEzYsYAcoSn51

