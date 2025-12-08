import sys
import os
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")
print(f"Files in CWD: {os.listdir('.')}")

try:
    import tensorflow as tf
    print(f"TensorFlow imported: {tf}")
    try:
        print(f"TF File: {tf.__file__}")
    except:
        print("TF has no __file__")
        
    try:
        print(f"TF Version: {tf.__version__}")
    except:
        print("TF has no __version__")

except ImportError as e:
    print(f"ImportError tensorflow: {e}")

try:
    import onnxruntime
    print(f"ONNX Runtime: {onnxruntime.__version__}")
except ImportError as e:
    print(f"ImportError onnxruntime: {e}")

try:
    import tflite_runtime.interpreter as tflite
    print(f"TFLite Runtime: {tflite}")
except ImportError as e:
    print(f"ImportError tflite_runtime: {e}")


