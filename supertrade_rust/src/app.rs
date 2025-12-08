use eframe::egui;
use egui_plot::{Line, Plot, PlotPoints};
use std::sync::{Arc, Mutex};

use std::time::{Duration, Instant};

use crate::bot_bridge::{BotBridge, BotStatus, ChartData};

pub struct SupertradeApp {
    bridge: Arc<Mutex<BotBridge>>,

    // UI State
    symbol: String,
    timeframe: String,
    poll_interval: i32,
    chart_refresh: i32,

    // Manual Trade State
    volume: f64,
    tp_points: i32,
    sl_points: i32,

    // App State
    is_running: bool,
    status_text: String,
    logs: Vec<String>,

    // Data
    chart_data: Option<ChartData>,
    bot_status: Option<BotStatus>,
    last_update: Instant,
}

impl SupertradeApp {
    pub fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        let bridge = BotBridge::new().expect("Failed to initialize Python bridge");

        Self {
            bridge: Arc::new(Mutex::new(bridge)),
            symbol: "XAUUSD.m".to_string(),
            timeframe: "H4".to_string(),
            poll_interval: 300,
            chart_refresh: 5,
            volume: 0.01,
            tp_points: 1000,
            sl_points: 200,
            is_running: false,
            status_text: "Status: Stopped".to_string(),
            logs: vec!["Application started".to_string()],
            chart_data: None,
            bot_status: None,
            last_update: Instant::now(),
        }
    }

    fn update_data(&mut self) {
        if self.last_update.elapsed().as_secs() < self.chart_refresh as u64 {
            return;
        }

        if let Ok(bridge) = self.bridge.lock() {
            if let Ok(Some(data)) = bridge.get_latest_data() {
                self.chart_data = Some(data);
            }
            if let Ok(Some(status)) = bridge.get_status() {
                self.bot_status = Some(status);
            }
        }
        self.last_update = Instant::now();
    }

    fn log(&mut self, msg: &str) {
        let timestamp = chrono::Local::now().format("%H:%M:%S");
        self.logs.push(format!("[{}] {}", timestamp, msg));
    }
}

impl eframe::App for SupertradeApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Periodic updates
        self.update_data();
        ctx.request_repaint_after(Duration::from_millis(1000));

        egui::CentralPanel::default().show(ctx, |ui| {
            // --- Controls ---
            ui.group(|ui| {
                ui.heading("Controls");
                ui.horizontal(|ui| {
                    if ui
                        .add_enabled(!self.is_running, egui::Button::new("Start Bot"))
                        .clicked()
                    {
                        let start_result = if let Ok(bridge) = self.bridge.lock() {
                            let _ = bridge.update_config(
                                &self.symbol,
                                &self.timeframe,
                                self.poll_interval,
                            );
                            Some(bridge.start())
                        } else {
                            None
                        };

                        match start_result {
                            Some(Ok(_)) => {
                                self.is_running = true;
                                self.status_text = "Status: Running".to_string();
                                self.log("Bot started");
                            }
                            Some(Err(e)) => {
                                self.log(&format!("Error starting bot: {:?}", e));
                            }
                            None => {}
                        }
                    }

                    if ui
                        .add_enabled(self.is_running, egui::Button::new("Stop Bot"))
                        .clicked()
                    {
                        let stop_result = if let Ok(bridge) = self.bridge.lock() {
                            Some(bridge.stop())
                        } else {
                            None
                        };

                        match stop_result {
                            Some(Ok(_)) => {
                                self.is_running = false;
                                self.status_text = "Status: Stopped".to_string();
                                self.log("Bot stopped");
                            }
                            Some(Err(e)) => {
                                self.log(&format!("Error stopping bot: {:?}", e));
                            }
                            None => {}
                        }
                    }

                    ui.separator();

                    ui.label("Symbol:");
                    ui.text_edit_singleline(&mut self.symbol);

                    ui.label("TF:");
                    egui::ComboBox::from_id_source("timeframe")
                        .selected_text(&self.timeframe)
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.timeframe, "M1".to_string(), "M1");
                            ui.selectable_value(&mut self.timeframe, "M5".to_string(), "M5");
                            ui.selectable_value(&mut self.timeframe, "M15".to_string(), "M15");
                            ui.selectable_value(&mut self.timeframe, "M30".to_string(), "M30");
                            ui.selectable_value(&mut self.timeframe, "H1".to_string(), "H1");
                            ui.selectable_value(&mut self.timeframe, "H4".to_string(), "H4");
                            ui.selectable_value(&mut self.timeframe, "D1".to_string(), "D1");
                            ui.selectable_value(&mut self.timeframe, "W1".to_string(), "W1");
                            ui.selectable_value(&mut self.timeframe, "MN".to_string(), "MN");
                        });

                    ui.label("Interval (s):");
                    ui.add(egui::DragValue::new(&mut self.poll_interval));

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(&self.status_text);
                    });
                });
            });

            ui.add_space(10.0);

            // --- Market Info ---
            ui.group(|ui| {
                ui.heading("Market Info");
                ui.horizontal(|ui| {
                    if let Some(status) = &self.bot_status {
                        ui.label(format!("Symbol: {}", status.symbol));
                        ui.separator();
                        ui.label(format!("Price: {:.2}", status.price));
                        ui.separator();
                        ui.label(format!("Signal: {} ({})", status.signal, status.confidence));
                    } else {
                        ui.label("Waiting for data...");
                    }
                });
            });

            ui.add_space(10.0);

            // --- Manual Trade ---
            ui.group(|ui| {
                ui.heading("Manual Trade");
                ui.horizontal(|ui| {
                    ui.label("Vol:");
                    ui.add(egui::DragValue::new(&mut self.volume).speed(0.01));

                    ui.label("TP (pts):");
                    ui.add(egui::DragValue::new(&mut self.tp_points));

                    ui.label("SL (pts):");
                    ui.add(egui::DragValue::new(&mut self.sl_points));

                    if ui.button("BUY").clicked() {
                        let manual_buy = {
                            if let Ok(bridge) = self.bridge.lock() {
                                bridge
                                    .manual_trade(0, self.volume, self.sl_points, self.tp_points)
                                    .is_ok()
                            } else {
                                false
                            }
                        };
                        if manual_buy {
                            self.log("Manual BUY requested");
                        }
                    }

                    if ui.button("SELL").clicked() {
                        let manual_sell = {
                            if let Ok(bridge) = self.bridge.lock() {
                                bridge
                                    .manual_trade(1, self.volume, self.sl_points, self.tp_points)
                                    .is_ok()
                            } else {
                                false
                            }
                        };
                        if manual_sell {
                            self.log("Manual SELL requested");
                        }
                    }
                });
            });

            // --- Chart ---
            ui.group(|ui| {
                ui.heading("Price Chart");
                let height = ui.available_height() * 0.6;

                Plot::new("price_chart").height(height).show(ui, |plot_ui| {
                    if let Some(data) = &self.chart_data {
                        let points: PlotPoints = data
                            .time
                            .iter()
                            .zip(data.close.iter())
                            .map(|(t, c)| [*t, *c])
                            .collect();
                        plot_ui.line(Line::new(points));
                    }
                });
            });

            ui.add_space(10.0);

            // --- Logs ---
            ui.group(|ui| {
                ui.heading("Logs");
                egui::ScrollArea::vertical()
                    .stick_to_bottom(true)
                    .show(ui, |ui| {
                        for log in &self.logs {
                            ui.label(log);
                        }
                    });
            });
        });
    }
}
