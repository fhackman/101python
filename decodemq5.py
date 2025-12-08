import re
import os

class MQ5Parser:
    def __init__(self):
        self.properties = {}
        self.inputs = {}
        self.functions = {}
        self.global_vars = {}
        
    def parse_file(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Parse properties
        property_pattern = r'#property\s+(\w+)\s+"(.+)"'
        self.properties = dict(re.findall(property_pattern, content))
        
        # Parse input parameters
        input_pattern = r'input\s+(\w+)\s+(\w+)\s*=\s*([^;]+);(?:\s*\/\/\s*(.+))?'
        for dtype, name, value, comment in re.findall(input_pattern, content):
            self.inputs[name] = {
                'type': dtype,
                'value': value.strip(),
                'comment': comment.strip() if comment else None
            }
        
        # Parse functions
        function_pattern = r'(\w+)\s+(\w+)\s*\((.*?)\)\s*{(.*?)}'
        for return_type, name, params, body in re.findall(function_pattern, content, re.DOTALL):
            self.functions[name] = {
                'return_type': return_type,
                'parameters': [p.strip() for p in params.split(',') if p.strip()],
                'body': body.strip()
            }
        
        # Parse global variables
        global_var_pattern = r'(?:^|\n)(\w+)\s+(\w+)\s*=\s*([^;]+);'
        self.global_vars = dict(re.findall(global_var_pattern, content))

    def get_trading_logic(self):
        if 'OnTick' in self.functions:
            return self.functions['OnTick']['body']
        return None

    def extract_indicators(self):
        indicators = []
        indicator_pattern = r'i[A-Z]\w+\('
        
        for func_name, func_data in self.functions.items():
            indicators.extend(re.findall(indicator_pattern, func_data['body']))
        
        return list(set(indicators))

# Example usage
def analyze_mq5_file(file_path):
    parser = MQ5Parser()
    parser.parse_file(file_path)
    
    print("=== MQ5 Analysis Report ===")
    
    print("\nProperties:")
    for key, value in parser.properties.items():
        print(f"  {key}: {value}")
    
    print("\nInput Parameters:")
    for name, data in parser.inputs.items():
        comment_str = f" // {data['comment']}" if data['comment'] else ""
        print(f"  {data['type']} {name} = {data['value']}{comment_str}")
    
    print("\nFunctions:")
    for name, data in parser.functions.items():
        params_str = ', '.join(data['parameters'])
        print(f"  {data['return_type']} {name}({params_str})")
    
    print("\nGlobal Variables:")
    for name, value in parser.global_vars.items():
        print(f"  {name} = {value}")
    
    print("\nIndicators Used:")
    indicators = parser.extract_indicators()
    for indicator in indicators:
        print(f"  {indicator}")
    
    trading_logic = parser.get_trading_logic()
    if trading_logic:
        print("\nTrading Logic Preview (OnTick function):")
        preview = trading_logic[:200] + "..." if len(trading_logic) > 200 else trading_logic
        print(f"  {preview}")

# Example test function
def test_parser():
    test_content = '''
    #property copyright "Test Strategy"
    #property version   "1.00"
    
    input int StopLoss = 100;    // Stop Loss in points
    input double LotSize = 0.1;  // Trading lot size
    
    int globalVar = 42;
    
    void OnTick()
    {
        if(iRSI(Symbol(), PERIOD_CURRENT, 14, PRICE_CLOSE) < 30)
        {
            OrderSend(Symbol(), OP_BUY, LotSize, Ask, 3, Bid - StopLoss * Point, 0);
        }
    }
    '''
    
    with open('test_strategy.mq5', 'w') as f:
        f.write(test_content)
    
    print("Testing MQ5 parser with sample strategy...")
    analyze_mq5_file('test_strategy.mq5')
    os.remove('test_strategy.mq5')

if __name__ == "__main__":
    test_parser()