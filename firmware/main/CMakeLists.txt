idf_component_register(SRCS "main.cpp" "preprocess.cpp" "fully_connected_reference.cpp"
    INCLUDE_DIRS "."
    PRIV_REQUIRES esp_driver_i2s esp_driver_uart esp_timer
    EMBED_FILES "model.tflite" "reference_audio.pcm" "reference_input.bin" "reference_output.bin")
target_compile_features(${COMPONENT_LIB} PRIVATE cxx_std_20)
target_compile_definitions(${COMPONENT_LIB} PRIVATE TF_LITE_STATIC_MEMORY)
