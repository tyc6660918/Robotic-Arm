from ursina import *

app = Ursina()
window.title = "DIAGNOSTIC"
window.size = (800, 600)
window.color = color.rgb(40, 40, 50)

# Big red cube at origin - should be VERY visible
Entity(model="cube", scale=0.5, color=color.red, unlit=True)

# Big green cube offset
Entity(model="cube", scale=0.3, position=(1, 0, 0), color=color.green, unlit=True)

# Big blue sphere
Entity(model="sphere", scale=0.4, position=(0, 1, 0), color=color.blue, unlit=True)

# White ground plane
Entity(model="plane", scale=10, position=(0, 0, -1), color=color.gray)

camera.position = (2, -3, 2)
camera.look_at((0.5, 0, 0))
EditorCamera()

print("Should see: red cube, green cube, blue sphere, gray floor")
app.run()
