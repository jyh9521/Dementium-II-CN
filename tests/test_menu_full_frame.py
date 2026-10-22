"""Registered WndProc -> native queue -> full native ImGui Checkbox frames."""
import os
from pathlib import Path
import unittest
from native_imgui_replay import ImGuiReplay

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE',ROOT/'build/full-zh-CN/Dementium II.exe'))

@unittest.skipUnless(SOURCE.is_file(),'requires supplied native executable')
class CompleteNativeMenuFrameTests(unittest.TestCase):
    image_base=None
    def setUp(self):
        self.vm=ImGuiReplay(SOURCE,image_base=self.image_base)
        self.vm.initialize_message_path()
        self.vm.initialize_imgui()
        self.vm.open_menu()
        result=self.frame()
        left,top,right,bottom=result['rect']
        self.point=(int((left+right)/2),int((top+bottom)/2))
        self.message(0x200)
        self.frame()

    def message(self,message):
        self.vm.windows_mouse_message(message,*self.point)

    def frame(self):
        self.vm.native_owned_input_frame()
        return self.vm.complete_checkbox_frame()

    def test_registered_wndproc_one_second_hold_releases_into_actual_checkbox(self):
        self.message(0x201)
        states=[self.frame() for _ in range(60)]
        self.assertTrue(all(s['value']==0 for s in states),'native checkbox activates on release, not hold')
        self.assertEqual(states[-1]['owned'],1,'real NewFrame must own the registered-WndProc click')
        self.assertEqual(states[-1]['nav_disable_mouse'],0)
        self.assertEqual(states[-1]['hovered'],states[-1]['window'])
        self.message(0x202)
        result=self.frame()
        self.assertEqual((result['changed'],result['value']),(1,1),
                         'registered WndProc click did not reach actual Checkbox after complete NewFrame')
        self.assertEqual(self.frame()['value'],1,'idle must not toggle again')

    def test_two_complete_registered_wndproc_clicks_toggle_actual_native_checkbox(self):
        values=[]
        for message in (0x201,0x202,0x201,0x202):
            self.message(message)
            values.append(self.frame()['value'])
        self.assertEqual(values,[0,1,1,0])

class RelocatedCompleteNativeMenuFrameTests(CompleteNativeMenuFrameTests):
    image_base=0x180000000

if __name__=='__main__':unittest.main(verbosity=2)
