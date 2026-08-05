/// Scene IDs and names are generated from ZDPS's SceneTable.json during the
/// GitHub Actions build. This fallback keeps common maps available if the
/// upstream table cannot be downloaded temporarily.
class LiteSceneCatalog {
  const LiteSceneCatalog._();

  static const Map<int, String> names = <int, String>{
    7: 'Asteria Plains',
    8: 'Asterleeds',
    9: 'Bahamar Highlands',
    10: 'Montegnor Valley',
    11: 'Starland',
    71: 'Duskdye Woods',
    72: 'Everfall Forest',
    73: 'Windhowl Canyon',
    74: 'Underground District',
    75: "Skimmer's Lair",
    76: 'Land of Crimson Illusion',
    91: 'Sunken Corridor',
    92: 'Gloomy Depths',
    6043: 'Chaotic - Soundless City',
    6044: 'Chaotic - Soundless City',
    6045: 'Chaotic - Soundless City',
    6421: 'Chaotic - Soundless City',
    6422: 'Chaotic - Soundless City',
    6423: 'Chaotic - Soundless City',
    6521: 'Chaotic - Mech Facility',
    6522: 'Chaotic - Mech Facility',
    6523: 'Chaotic - Mech Facility',
    6524: 'Chaotic - Mech Facility',
    6525: 'Chaotic - Mech Facility',
    12000: 'Guild Center',
    12011: 'Guild Hunt - Hard',
    12012: 'Guild Hunt - Normal',
    12013: 'Guild Hunt - Easy',
    12014: 'Guild Hunt - Normal',
    12015: 'Guild Hunt - Hard',
    12018: 'Guild Hunt - Normal',
    12019: 'Guild Hunt - Hard',
    12022: 'Guild Hunt - Normal',
    12023: 'Guild Hunt - Hard',
  };

  static String? nameFor(int mapId) => names[mapId];
  static bool contains(int mapId) => names.containsKey(mapId);
}
