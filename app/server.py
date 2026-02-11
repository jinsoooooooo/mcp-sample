from fastmcp import FastMCP
# from config import settings


# 1. 서버 인스턴스 생성
mcp = FastMCP("My FastMCP Server")

# 2. @mcp.tool 데코레이터로 함수를 '도구'로 등록
@mcp.tool
def add(a:int, b:int) -> int:
    """Add two numbers"""
    return a+b


# 3. 서버 실행 (스크립트가 직접 실행될 때만)
if __name__ == "__main__":
    mcp.run()

