"""Actual PE menu/reader/focus lifecycle audit; no game or saves are opened.

Registered-WndProc focus messages, Win32 key translation/callback wrappers,
native F1 visibility edges, native cursor ownership, and complete native ImGui
frames execute the selected PE. Imported APIs retain deterministic boundaries.
"""
import os
from pathlib import Path
import struct
import unittest
from native_imgui_replay import ImGuiReplay

ROOT=Path(__file__).resolve().parents[1]
EXE=Path(os.environ.get('DEMENTIUM_UI_TEST_EXE') or os.environ.get('DEMENTIUM_MODIFIED_EXE') or ROOT/'build/full-zh-CN/Dementium II.exe')

@unittest.skipUnless(EXE.is_file(),'requires a locally supplied modified PE')
class MenuTransitionAuditTests(unittest.TestCase):
    image_base=None
    def setUp(self):
        self.v=v=ImGuiReplay(EXE,image_base=self.image_base)
        v.initialize_message_path()
        v.initialize_imgui()
        v.rect=(0,0,1280,720)
        v.run(0x2f171,stop=0x2f199)  # actual startup disables native direct mode
        self.assertEqual(self.field(0x458),0)

    def field(self,offset):return self.v.uc.mem_read(self.v.obj+offset,1)[0]
    def window_field(self,offset):return self.v.uc.mem_read(self.v.window+offset,1)[0]
    def key(self,vk,pressed):
        v=self.v;internal=v.run(0x2dd940,rcx=vk)
        v.run(0x1a7dc0 if pressed else 0x1a7de0,rcx=internal)
        return internal
    def focus_frame(self):
        v=self.v;v.run(0x4fa66,stop=0x4fa6e,rcx=1,rax=v.byte(0x4a2f1d))
    def f1_toggle(self):
        v=self.v;self.key(0x70,1)
        v.run(0x4fa2e,stop=0x4fa6e,rcx=self.field(0x22c),rsi=0)
        self.key(0x70,0)
        v.run(0x4fa2e,stop=0x4fa6e,rcx=self.field(0x22c),rsi=0)
        return v.byte(0x4a2f1d)
    def windows_key(self,vk,pressed):
        self.v.run(0x2f3650,rcx=0x1234,rdx=0x100 if pressed else 0x101,
                   r8=vk,r9=1 if pressed else (1<<31)|(1<<30)|1)
    def toggle_frame(self):
        self.v.run(0x4fa2e,stop=0x4fa6e,rcx=self.field(0x22c),rsi=0)
    def app_active(self,active):
        self.v.run(0x2f3650,rcx=0x1234,rdx=0x1c,r8=int(active),r9=0)
    def keyboard_focus(self,focused):
        self.v.run(0x2f3650,rcx=0x1234,rdx=7 if focused else 8,r8=0,r9=0)
    def gui_frame(self):
        self.v.native_owned_input_frame()
        return self.v.complete_checkbox_frame()

    def test_all_menu_held_keys_are_neutral_after_close_and_late_keyup(self):
        self.assertEqual(self.f1_toggle(),1)
        keys=[(0x0d,0x221),(0x1b,0x222),(0x41,0x223),(0x53,0x224),
              (0x57,0x226),(0x45,0x227),(0x26,0x22d),(0x28,0x22e),
              (0x25,0x22f),(0x27,0x230)]
        for vk,offset in keys:
            self.key(vk,1)
            self.assertEqual(self.field(offset),1,(vk,offset))
        self.assertEqual(self.f1_toggle(),0)
        for vk,offset in keys:
            self.assertEqual(self.field(offset),0,('close left held field',vk,offset))
            self.key(vk,0)
            self.assertEqual(self.field(offset),0,('mode-gated release left field',vk,offset))
        self.assertEqual(self.field(0x458),0)
        self.assertEqual(self.f1_toggle(),1,'F1 debounce must remain usable after held-key cleanup')

    def test_menu_close_restores_capture_only_while_both_native_focus_states_are_active(self):
        self.assertEqual(self.f1_toggle(),1)
        self.assertEqual(self.v.byte(0xa68e82),1,'pre-menu capture must be retained')
        self.app_active(False)
        self.assertEqual((self.window_field(0x79),self.window_field(0x7a)),(1,0))
        self.focus_frame()
        self.assertEqual(self.v.byte(0xa68e81),0)
        self.assertEqual(self.window_field(0x19),0)
        self.v.calls.clear()
        # Visibility can change independently of focus (e.g. pending UI/action
        # teardown). This is a state-transition audit, not an OS key-delivery claim.
        self.v.byte(0x4a2f1d,0)
        self.focus_frame()
        clips=[c[3] for c in self.v.calls if c[0]=='ClipCursor']
        hidden=any(c[0]=='SetCursor' and c[1]==0 for c in self.v.calls)
        print('MENU_CLOSE_INACTIVE focus79=%d active7a=%d capture19=%d clips=%s cursor_hidden=%s'%
              (self.window_field(0x79),self.window_field(0x7a),self.window_field(0x19),clips,hidden))
        self.assertEqual(self.window_field(0x19),0,'inactive application must not regain game capture on menu teardown')
        self.assertFalse(any(c is not None for c in clips),'inactive menu close must not clip the cursor again')
        self.assertFalse(hidden,'inactive menu close must not hide the OS cursor')

    def test_registered_f1_new_press_after_unfocused_release_is_not_lost(self):
        # Real WM_KEYDOWN repeat suppression precedes the callback. The OS does
        # not deliver the release to this game when another app owns focus.
        self.windows_key(0x70,True);self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),1)
        self.app_active(False);self.keyboard_focus(False);self.focus_frame()
        self.toggle_frame()  # a background frame must observe release cleanup
        self.app_active(True);self.keyboard_focus(True);self.focus_frame()
        self.windows_key(0x70,True);self.toggle_frame()
        print('F1_REFOCUS visible=%d field22c=%d debounce=%d vk_repeat=%d'%
              (self.v.byte(0x4a2f1d),self.field(0x22c),self.v.byte(0xa34527),self.v.byte(0xa30d90)))
        self.assertEqual(self.v.byte(0x4a2f1d),0,
                         'first fresh F1 press after a release in another app must close the menu')
        self.windows_key(0x70,False);self.toggle_frame()
        self.windows_key(0x70,True);self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),1)

    def test_registered_f1_held_autorepeat_after_refocus_does_not_toggle(self):
        self.windows_key(0x70,True);self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),1)
        self.app_active(False);self.keyboard_focus(False);self.focus_frame()
        self.toggle_frame()
        self.app_active(True);self.keyboard_focus(True);self.focus_frame()
        # The key never physically released: Windows reports previous-state=1.
        self.v.run(0x2f3650,rcx=0x1234,rdx=0x100,r8=0x70,r9=(1<<30)|1)
        self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),1,
                         'a still-held F1 autorepeat after refocus must not toggle the menu')
        self.v.run(0x2f3650,rcx=0x1234,rdx=0x104,r8=0x70,r9=(1<<30)|1)
        self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),1,
                         'WM_SYSKEYDOWN autorepeat must follow the same repeat suppression')
        self.windows_key(0x70,False);self.toggle_frame()
        self.windows_key(0x70,True);self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),0,'release and a new press must still toggle')

    def test_registered_f1_normal_release_before_focus_change_stays_usable(self):
        self.windows_key(0x70,True);self.toggle_frame()
        self.windows_key(0x70,False);self.toggle_frame()
        self.app_active(False);self.keyboard_focus(False);self.focus_frame()
        self.app_active(True);self.keyboard_focus(True);self.focus_frame()
        self.windows_key(0x70,True);self.toggle_frame()
        self.assertEqual(self.v.byte(0x4a2f1d),0)

    def test_keyboard_focus_loss_close_does_not_restore_capture(self):
        self.f1_toggle();self.keyboard_focus(False);self.focus_frame()
        self.v.byte(0x4a2f1d,0);self.focus_frame()
        self.assertEqual(self.window_field(0x79),0)
        self.assertEqual(self.window_field(0x19),0)

    def test_focused_close_restores_pre_menu_game_capture(self):
        self.f1_toggle();self.f1_toggle()
        self.assertEqual((self.window_field(0x79),self.window_field(0x7a),self.window_field(0x19)),(1,1,1))

    def test_menu_over_reader_held_keys_do_not_remain_after_menu_close(self):
        v=self.v;v.write(0xa68980,struct.pack('<I',1))
        self.key(0x26,1);self.assertEqual(self.field(0x22d),1)
        self.f1_toggle()
        self.key(0x0d,1);self.key(0x45,1)
        self.assertEqual(self.field(0x221),1);self.assertEqual(self.field(0x227),1)
        self.f1_toggle()
        for offset in (0x221,0x227,0x22d):self.assertEqual(self.field(offset),0)
        self.key(0x0d,0);self.key(0x45,0);self.key(0x26,0)
        self.assertEqual(v.dword(0xa68980),1,'menu cleanup must not close underlying reader')
        self.assertEqual(self.field(0x458),0)
        self.key(0x26,1);self.assertEqual(self.field(0x22d),1)
        self.key(0x26,0);self.assertEqual(self.field(0x22d),0)

    def test_real_active_widget_held_across_menu_close_cannot_click_on_reopen(self):
        v=self.v;self.f1_toggle()
        result=self.gui_frame();a,b,c,d=result['rect'];point=(int((a+c)/2),int((b+d)/2))
        v.windows_mouse_message(0x200,*point);self.gui_frame()
        v.windows_mouse_message(0x201,*point);self.gui_frame()
        self.assertNotEqual(struct.unpack('<I',v.uc.mem_read(v.io+0x1af8,4))[0],0)
        self.assertEqual(self.f1_toggle(),0)
        self.assertEqual(self.field(0x231),0)
        self.assertEqual(struct.unpack('<I',v.uc.mem_read(v.io+0x1af8,4))[0],0)
        self.assertEqual(self.f1_toggle(),1)
        v.windows_mouse_message(0x200,*point);self.assertEqual(self.gui_frame()['value'],0)
        v.windows_mouse_message(0x202,*point);self.assertEqual(self.gui_frame()['value'],0)
        v.windows_mouse_message(0x201,*point);self.gui_frame()
        v.windows_mouse_message(0x202,*point);self.assertEqual(self.gui_frame()['value'],1)

    def test_real_active_widget_is_canceled_on_focus_loss_and_reopen_needs_new_click(self):
        v=self.v;self.f1_toggle()
        result=self.gui_frame();a,b,c,d=result['rect'];point=(int((a+c)/2),int((b+d)/2))
        v.windows_mouse_message(0x200,*point);self.gui_frame()
        v.windows_mouse_message(0x201,*point);result=self.gui_frame()
        self.assertEqual(result['value'],0)
        self.assertNotEqual(struct.unpack('<I',v.uc.mem_read(v.io+0x1af8,4))[0],0)
        self.app_active(False);self.focus_frame()
        self.assertEqual(struct.unpack('<I',v.uc.mem_read(v.io+0x1af8,4))[0],0,'focus loss must clear real native widget ActiveId')
        self.app_active(True);self.focus_frame()
        v.windows_mouse_message(0x200,*point);self.assertEqual(self.gui_frame()['value'],0)
        v.windows_mouse_message(0x202,*point);self.assertEqual(self.gui_frame()['value'],0,'old held click must not activate after refocus')
        v.windows_mouse_message(0x201,*point);self.gui_frame()
        v.windows_mouse_message(0x202,*point);self.assertEqual(self.gui_frame()['value'],1)

class RelocatedMenuTransitionAuditTests(MenuTransitionAuditTests):
    image_base=0x180000000

if __name__=='__main__':unittest.main(verbosity=2)
