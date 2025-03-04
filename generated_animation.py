from manim import *

class UserAnimationScene(Scene):
    def construct(self):
        # Create the sides of the triangle
        side_a = Line(ORIGIN, RIGHT*3)
        side_b = Line(ORIGIN, UP*4)
        side_c = Line(RIGHT*3, UP*4)

        # Create the squares for each side
        square_a = Square(side_length=3).next_to(side_a, DOWN, buff=0)
        square_b = Square(side_length=4).next_to(side_b, LEFT, buff=0)
        square_c = Square(side_length=5).next_to(side_c, buff=0)

        # Create labels for each side
        label_a = Tex("a").next_to(side_a, DOWN)
        label_b = Tex("b").next_to(side_b, LEFT)
        label_c = Tex("c").next_to(side_c, RIGHT)

        # Create labels for each square
        label_a_sq = Tex("a^2").move_to(square_a)
        label_b_sq = Tex("b^2").move_to(square_b)
        label_c_sq = Tex("c^2").move_to(square_c)

        # Create the theorem text
        theorem = Tex("a^2 + b^2 = c^2").to_edge(UP)

        # Animate the creation of the triangle and squares
        self.play(Create(side_a), Write(label_a))
        self.play(Create(side_b), Write(label_b))
        self.play(Create(side_c), Write(label_c))
        self.wait(1)
        self.play(Create(square_a), Write(label_a_sq))
        self.play(Create(square_b), Write(label_b_sq))
        self.play(Create(square_c), Write(label_c_sq))
        self.wait(1)

        # Animate the theorem text
        self.play(Write(theorem))
        self.wait(2)