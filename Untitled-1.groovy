#include <windows.h>
#include <iostream>
#include <string>
#include <vector>

class Unzipper {
private:
    std::wstring zipPath;
    std::wstring outputPath;

    bool ExtractFile(HANDLE hZip, const WIN32_FIND_DATA& fileData) {
        // Tạo đường dẫn đầu ra
        std::wstring outPath = outputPath + L"\\" + fileData.cFileName;
        
        // Tạo file đầu ra
        HANDLE hOut = CreateFileW(
            outPath.c_str(),
            GENERIC_WRITE,
            0,
            NULL,
            CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            NULL
        );
        
        if (hOut == INVALID_HANDLE_VALUE) {
            return false;
        }

        // Đọc và giải nén dữ liệu
        std::vector<BYTE> buffer(4096);
        DWORD bytesRead, bytesWritten;
        
        while (ReadFile(hZip, buffer.data(), buffer.size(), &bytesRead, NULL) 
               && bytesRead > 0) {
            // Ở đây sẽ thêm logic giải nén dữ liệu
            // buffer chứa dữ liệu đã nén, cần giải nén trước khi ghi
            
            if (!WriteFile(hOut, buffer.data(), bytesRead, &bytesWritten, NULL)) {
                CloseHandle(hOut);
                return false;
            }
        }

        CloseHandle(hOut);
        return true;
    }

public:
    Unzipper(const std::wstring& zipFile, const std::wstring& outDir) 
        : zipPath(zipFile), outputPath(outDir) {}

    bool Extract() {
        // Mở file zip
        HANDLE hZip = CreateFileW(
            zipPath.c_str(),
            GENERIC_READ,
            FILE_SHARE_READ,
            NULL,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            NULL
        );

        if (hZip == INVALID_HANDLE_VALUE) {
            return false;
        }

        // Tạo thư mục đầu ra nếu chưa tồn tại
        CreateDirectoryW(outputPath.c_str(), NULL);

        // Đọc central directory để lấy danh sách file
        WIN32_FIND_DATA fileData;
        bool success = true;

        // Đọc từng file trong archive và giải nén
        while (success && ReadFile(hZip, &fileData, sizeof(fileData), NULL, NULL)) {
            if (fileData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                // Tạo thư mục
                std::wstring dirPath = outputPath + L"\\" + fileData.cFileName;
                CreateDirectoryW(dirPath.c_str(), NULL);
            } else {
                // Giải nén file
                success = ExtractFile(hZip, fileData);
            }
        }

        CloseHandle(hZip);
        return success;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cout << "Usage: unzip <zipfile> <output_dir>\n";
        return 1;
    }

    // Chuyển đổi tham số thành Unicode
    int bufSize = MultiByteToWideChar(CP_UTF8, 0, argv[1], -1, NULL, 0);
    std::vector<wchar_t> zipPath(bufSize);
    MultiByteToWideChar(CP_UTF8, 0, argv[1], -1, zipPath.data(), bufSize);

    bufSize = MultiByteToWideChar(CP_UTF8, 0, argv[2], -1, NULL, 0);
    std::vector<wchar_t> outPath(bufSize);
    MultiByteToWideChar(CP_UTF8, 0, argv[2], -1, outPath.data(), bufSize);

    // Tạo đối tượng unzipper và thực hiện giải nén
    Unzipper unzipper(zipPath.data(), outPath.data());
    
    if (unzipper.Extract()) {
        std::cout << "Extraction completed successfully.\n";
        return 0;
    } else {
        std::cout << "Failed to extract files.\n";
        return 1;
    }
}

// Compilation command
// g++ -o unzip.exe unzip.cpp -lzunzip.exe archive.zip output_folderg++ -o unzip.exe unzip.cpp -lz