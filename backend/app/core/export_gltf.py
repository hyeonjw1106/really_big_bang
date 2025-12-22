import bpy
import sys
import os


def export_scene(output_path):
    """Exports the current scene to a .glb file."""
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format='GLB',
            use_selection=False,  # Export the whole scene
            export_apply=True,    # Apply modifiers
            export_cameras=True,
            export_lights=True,
        )
        print(f"Successfully exported to {output_path}")
        return True
    except Exception as e:
        print(f"Error exporting to glTF: {e}", file=sys.stderr)
        # It's useful to print the full traceback for debugging
        import traceback
        traceback.print_exc(file=sys.stderr)
        return False

if __name__ == "__main__":
    # This allows running the script from Blender's command line
    # Example: blender my_scene.blend --python export_gltf.py -- /path/to/output.glb
    argv = sys.argv
    try:
        # Get the arguments after '--'
        if "--" in argv:
            args = argv[argv.index("--") + 1:]
            if not args:
                raise ValueError("No output path provided.")
            output_filepath = args[0]
            if not export_scene(output_filepath):
                sys.exit(1)
        else:
            raise ValueError("Separator '--' not found in arguments.")
    except ValueError as err:
        print(f"Argument error: {err}", file=sys.stderr)
        print("Usage: blender <blend_file> --python export_gltf.py -- <output_path.glb>", file=sys.stderr)
        sys.exit(1)
