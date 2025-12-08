use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BotStatus {
    pub timestamp: String,
    pub symbol: String,
    pub signal: String,
    pub confidence: String,
    pub price: f64,
}

#[derive(Clone, Debug)]
pub struct ChartData {
    pub time: Vec<f64>,
    pub close: Vec<f64>,
}

pub struct BotBridge {
    bot_instance: PyObject,
}

impl BotBridge {
    pub fn new() -> PyResult<Self> {
        Python::with_gil(|py| {
            // Add current directory to sys.path
            let sys = py.import("sys")?;
            let path = sys.getattr("path")?;
            path.call_method1("append", (".",))?;
            path.call_method1("append", ("..",))?;

            // Import supertrade module
            let supertrade = py.import("supertrade")?;
            let config = supertrade.getattr("CONFIG")?;

            // Instantiate bot
            let bot_class = supertrade.getattr("SuperpointTradingBot")?;
            let bot_instance = bot_class.call1((config,))?.into();

            Ok(BotBridge { bot_instance })
        })
    }

    pub fn start(&self) -> PyResult<()> {
        Python::with_gil(|py| {
            // We need to run this in a thread on the Python side or handle threading here.
            // The original GUI used threading.Thread(target=self.bot.run).
            // We can do the same via Python's threading module.
            let threading = py.import("threading")?;
            let target = self.bot_instance.getattr(py, "run")?;

            let thread = threading.call_method1("Thread", ((), target))?;
            thread.setattr("daemon", true)?;
            thread.call_method0("start")?;

            Ok(())
        })
    }

    pub fn stop(&self) -> PyResult<()> {
        Python::with_gil(|py| {
            self.bot_instance.call_method0(py, "stop")?;
            Ok(())
        })
    }

    pub fn update_config(&self, symbol: &str, _timeframe: &str, interval: i32) -> PyResult<()> {
        Python::with_gil(|py| {
            let config = self.bot_instance.getattr(py, "config")?;
            config.call_method1(py, "__setitem__", ("SYMBOL", symbol))?;
            // Timeframe mapping would ideally happen here or pass integer
            // For simplicity, we'll assume the Python side handles string or we pass int
            // But supertrade.py expects MT5 constants (ints).
            // Let's just update symbol and interval for now to avoid complexity with MT5 constants import
            config.call_method1(py, "__setitem__", ("POLL_INTERVAL", interval))?;
            Ok(())
        })
    }

    pub fn manual_trade(&self, signal: i32, volume: f64, sl: i32, tp: i32) -> PyResult<()> {
        Python::with_gil(|py| {
            let threading = py.import("threading")?;
            let target = self.bot_instance.getattr(py, "manual_trade")?;
            let args = (signal, volume, sl, tp);

            let thread = threading.call_method1("Thread", ((), target, args))?;
            thread.call_method0("start")?;
            Ok(())
        })
    }

    pub fn get_latest_data(&self) -> PyResult<Option<ChartData>> {
        Python::with_gil(|py| {
            let latest_data = self.bot_instance.getattr(py, "latest_data")?;
            if latest_data.is_none(py) {
                return Ok(None);
            }

            // Convert pandas DataFrame to vectors
            // Assuming df has index 'time' and column 'close'

            // Convert datetime index to timestamps (float)
            // This might be tricky without pandas knowledge, but let's try casting to int/float
            // Or we can use a helper in Python

            // Let's use a small python snippet to extract lists
            let locals = PyDict::new(py);
            locals.set_item("df", latest_data)?;

            let py_code = "
timestamps = df.index.astype('int64') // 10**9 # Convert ns to seconds
closes = df['close'].values.tolist()
timestamps = timestamps.tolist()
";
            py.run(py_code, None, Some(locals))?;

            let timestamps: Vec<f64> = locals.as_ref().get_item("timestamps")?.extract()?;
            let closes: Vec<f64> = locals.as_ref().get_item("closes")?.extract()?;

            Ok(Some(ChartData {
                time: timestamps,
                close: closes,
            }))
        })
    }

    pub fn get_status(&self) -> PyResult<Option<BotStatus>> {
        Python::with_gil(|py| {
            let status = self.bot_instance.getattr(py, "latest_status")?;
            if status.is_none(py) {
                return Ok(None);
            }

            let dict = status.downcast::<PyDict>(py).map_err(|_| {
                PyErr::new::<pyo3::exceptions::PyTypeError, _>("Status is not a dict")
            })?;

            let timestamp: String = dict.as_ref().get_item("timestamp")?.extract()?;
            let symbol: String = dict.as_ref().get_item("symbol")?.extract()?;
            let signal: String = dict.as_ref().get_item("signal")?.extract()?;
            let confidence: String = dict.as_ref().get_item("confidence")?.extract()?;
            let price: f64 = dict.as_ref().get_item("price")?.extract()?;

            Ok(Some(BotStatus {
                timestamp,
                symbol,
                signal,
                confidence,
                price,
            }))
        })
    }
}
