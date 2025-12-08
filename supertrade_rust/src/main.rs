use eframe::egui;

mod app;
mod bot_bridge;

use app::SupertradeApp;

fn main() -> Result<(), eframe::Error> {
    // Initialize Python environment
    pyo3::prepare_freethreaded_python();

    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([1000.0, 850.0]),
        ..Default::default()
    };

    eframe::run_native(
        "Superpoint Trading Bot",
        options,
        Box::new(|cc| Box::new(SupertradeApp::new(cc))),
    )
}
