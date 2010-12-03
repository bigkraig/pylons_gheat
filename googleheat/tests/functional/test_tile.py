from googleheat.tests import *

class TestTileController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='tile', action='index'))
        # Test response...
