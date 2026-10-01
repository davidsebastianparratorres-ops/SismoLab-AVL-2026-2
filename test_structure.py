import unittest
from src.models.Point import Point
from src.models.Zone import Zone
from src.rules.ZoneClassifier import ZoneClassifier
from src.rules.PriorityCalculator import PriorityCalculator


class TestZoneAndPriorityRules(unittest.TestCase):
    """Batería de pruebas unitarias para la validación de Zonas, Bordes y Prioridades.
    
    Cubre los requerimientos de las Secciones 3, 4 y los casos mínimos de la Sección 16.
    """

    def setUp(self):
        """Configuración del escenario con zonas adyacentes que comparten frontera."""
        self.classifier = ZoneClassifier()

        # Zona 1: No Poblada (Reserva) -> [0, 500] en X, [0, 1000] en Y
        self.z1_rural = Zone(
            x_min=0.0, x_max=500.0,
            y_min=0.0, y_max=1000.0,
            populated=False
        )

        # Zona 2: Poblada (Urbana) -> [500, 1000] en X, [0, 1000] en Y
        self.z2_urban = Zone(
            x_min=500.0, x_max=1000.0,
            y_min=0.0, y_max=1000.0,
            populated=True
        )

        self.classifier.add_zone(self.z1_rural)
        self.classifier.add_zone(self.z2_urban)

        # Puntos de prueba estratégicos
        self.border_point = Point(500.0, 300.0)    # Exactamente en la frontera X = 500.0
        self.rural_point = Point(250.0, 300.0)     # Dentro de la Zona No Poblada
        self.urban_point = Point(750.0, 300.0)     # Dentro de la Zona Poblada

    # -------------------------------------------------------------------------
    # 1. PRUEBAS DE REGLA DE BORDE Y PERTENENCIA (Sección 3)
    # -------------------------------------------------------------------------

    def test_border_colision_returns_populated(self):
        """Sección 3: Un punto en el borde compartido de dos zonas debe clasificarse 
        como Zona Poblada si al menos una de las zonas lo es."""
        is_populated = self.classifier.is_in_populated_zone(self.border_point)
        self.assertTrue(is_populated, "El borde compartido con una zona poblada debe clasificarse como Poblada.")

    def test_rural_point_returns_not_populated(self):
        """Un punto exclusivo en zona no poblada debe retornar False."""
        is_populated = self.classifier.is_in_populated_zone(self.rural_point)
        self.assertFalse(is_populated)

    # -------------------------------------------------------------------------
    # 2. CASOS MÍNIMOS OBLIGATORIOS (Sección 16 y Sección 4)
    # -------------------------------------------------------------------------

    def test_section_16_limit_case_border_high_priority(self):
        """Sección 16: M = 4.5, H = 30.0 km en borde de zona poblada debe dar Prioridad 3 (Alta)."""
        priority = PriorityCalculator.calculate_priority(
            magnitude=4.5,
            depth=30.0,
            epicenter=self.border_point,
            zone_classifier=self.classifier
        )
        self.assertEqual(priority, 3, "M=4.5, H=30.0 en zona poblada/borde debe ser Prioridad 3.")

    def test_section_16_limit_case_rural_medium_priority(self):
        """Sección 16: M = 4.5, H = 30.0 km FUERA de zona poblada debe dar Prioridad 2 (Media)."""
        priority = PriorityCalculator.calculate_priority(
            magnitude=4.5,
            depth=30.0,
            epicenter=self.rural_point,
            zone_classifier=self.classifier
        )
        self.assertEqual(priority, 2, "El mismo evento fuera de zona poblada debe ser Prioridad 2.")

    # -------------------------------------------------------------------------
    # 3. EVALUACIÓN DE LÍMITES Y CONDICIONES EXTREMAS DE PRIORIDAD (Sección 4)
    # -------------------------------------------------------------------------

    def test_magnitude_6_always_high_priority(self):
        """Sección 4: M >= 6.0 siempre es Prioridad 3 (Alta), independiente de H y zona."""
        # Evento profundo en zona rural
        p1 = PriorityCalculator.calculate_priority(6.0, 150.0, self.rural_point, self.classifier)
        # Evento superficial en zona urbana
        p2 = PriorityCalculator.calculate_priority(6.0, 10.0, self.urban_point, self.classifier)

        self.assertEqual(p1, 3)
        self.assertEqual(p2, 3)

    def test_depth_strict_boundary_30_0_km(self):
        """Evalúa el comportamiento inclusivo de H = 30.0 vs H = 30.1 km."""
        # H = 30.0 -> Cumple la condición de prioridad Alta
        p_exact = PriorityCalculator.calculate_priority(4.5, 30.0, self.urban_point, self.classifier)
        # H = 30.1 -> Excede el límite de 30.0 km, pasa a Prioridad Media
        p_exceeded = PriorityCalculator.calculate_priority(4.5, 30.1, self.urban_point, self.classifier)

        self.assertEqual(p_exact, 3, "H=30.0 km exactos debe ser inclusivo (Prioridad 3).")
        self.assertEqual(p_exceeded, 2, "H=30.1 km excede el límite y debe caer a Prioridad 2.")

    def test_low_priority_cases(self):
        """Sección 4: Eventos con M < 4.5 deben clasificarse como Prioridad 1 (Baja)."""
        # M = 4.4, muy superficial y en zona urbana -> Prioridad 1
        p_urban_low = PriorityCalculator.calculate_priority(4.4, 5.0, self.urban_point, self.classifier)
        # M = -1.0 (límite inferior permitido) -> Prioridad 1
        p_min_mag = PriorityCalculator.calculate_priority(-1.0, 10.0, self.rural_point, self.classifier)

        self.assertEqual(p_urban_low, 1)
        self.assertEqual(p_min_mag, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)