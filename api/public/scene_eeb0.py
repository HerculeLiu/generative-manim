
from manim import *
from math import *
config.frame_size = (3840, 2160)
config.frame_width = 14.22

from manim import *
from math import *

class GenScene(Scene):
    def construct(self):
        frame_width = config.frame_width
        frame_height = config.frame_height
        left_edge = -frame_width / 2
        bottom_edge = -frame_height / 2
        platform_y = bottom_edge + frame_height / 5
        wall_x = left_edge + frame_width / 5
        
        platform = Line(
            start=[left_edge, platform_y, 0],
            end=[left_edge + frame_width, platform_y, 0],
            color=WHITE,
            stroke_width=2
        )
        wall = Line(
            start=[wall_x, platform_y, 0],
            end=[wall_x, platform_y + frame_height * 0.6, 0],
            color=WHITE,
            stroke_width=2
        )
        self.add(platform, wall)
        
        small_width = 0.2
        small_height = 0.3
        large_width = 0.4
        large_height = 0.6
        small_x0 = left_edge + frame_width * 2/5
        large_x0 = left_edge + frame_width * 3/5
        small_slider = Rectangle(
            width=small_width,
            height=small_height,
            color=BLUE,
            fill_opacity=0.7
        )
        small_slider.move_to([small_x0, platform_y + small_height/2, 0])
        large_slider = Rectangle(
            width=large_width,
            height=large_height,
            color=RED,
            fill_opacity=0.7
        )
        large_slider.move_to([large_x0, platform_y + large_height/2, 0])
        small_label = Text("1 kg", font_size=20, color=BLUE)
        small_label.next_to(small_slider, UP, buff=0.1)
        large_label = Text("10000 kg", font_size=20, color=RED)
        large_label.next_to(large_slider, UP, buff=0.1)
        self.add(small_slider, large_slider, small_label, large_label)
        
        collision_text = Text("Collision Count 1: 0", font_size=24, color=WHITE)
        collision_text.to_corner(UL, buff=0.25)
        self.add(collision_text)
        
        m1 = 1.0
        m2 = 10000.0
        v1 = 0.0
        v2 = -1.0
        collision_count = 0
        
        def update_sliders(dt):
            nonlocal v1, v2, collision_count
            x1 = small_slider.get_center()[0]
            x2 = large_slider.get_center()[0]
            w1 = small_width
            w2 = large_width
            
            x1_new = x1 + v1 * dt
            x2_new = x2 + v2 * dt
            
            left1 = x1_new - w1/2
            right1 = x1_new + w1/2
            left2 = x2_new - w2/2
            right2 = x2_new + w2/2
            
            wall_collision = False
            if left1 <= wall_x:
                wall_collision = True
                x1_new = wall_x + w1/2
                v1 = -v1
                collision_count += 1
            
            block_collision = False
            if not wall_collision and right1 >= left2:
                block_collision = True
                overlap = right1 - left2
                x1_new -= overlap/2
                x2_new += overlap/2
                
                v1_new = ((m1 - m2)*v1 + 2*m2*v2) / (m1 + m2)
                v2_new = (2*m1*v1 + (m2 - m1)*v2) / (m1 + m2)
                v1, v2 = v1_new, v2_new
                collision_count += 1
            
            small_slider.move_to([x1_new, platform_y + small_height/2, 0])
            large_slider.move_to([x2_new, platform_y + large_height/2, 0])
            small_label.next_to(small_slider, UP, buff=0.1)
            large_label.next_to(large_slider, UP, buff=0.1)
            
            collision_text.become(Text(f"Collision Count: {collision_count}", font_size=24, color=WHITE).to_corner(UL, buff=0.25))
            
            if v1 > 0 and v2 > 0 and v2 > v1:
                self.remove_updater(update_sliders)
        
        self.add_updater(update_sliders)
        self.wait(30)
    