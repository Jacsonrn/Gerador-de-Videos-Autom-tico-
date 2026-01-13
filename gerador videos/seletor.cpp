#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <algorithm>
#include <random>
#include <deque>
#include <dirent.h> // Biblioteca antiga para ler pastas
#include <sys/stat.h>

// Configurações
const std::string ARQUIVO_HISTORICO = "historico.txt";
const int QTD_SELECAO = 40;
const int TAMANHO_HISTORICO = 300;

// --- FUNÇÕES AUXILIARES (Para substituir o filesystem) ---

// Função manual para copiar arquivos (já que não temos fs::copy_file)
bool copiarArquivo(const std::string& origem, const std::string& destino) {
    std::ifstream src(origem, std::ios::binary);
    std::ofstream dst(destino, std::ios::binary);
    if (!src || !dst) return false;
    dst << src.rdbuf();
    return true;
}

// Verifica se é imagem pela extensão
bool ehImagem(const std::string& nome) {
    std::string ext = "";
    size_t ponto = nome.find_last_of(".");
    if (ponto != std::string::npos) {
        ext = nome.substr(ponto);
    }
    // Converte para minúsculo
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    return (ext == ".jpg" || ext == ".jpeg" || ext == ".png" || ext == ".bmp" || ext == ".gif");
}

// Carrega histórico
std::deque<std::string> carregarHistorico() {
    std::deque<std::string> historico;
    std::ifstream arquivo(ARQUIVO_HISTORICO);
    std::string linha;
    if (arquivo.is_open()) {
        while (std::getline(arquivo, linha)) {
            if (!linha.empty()) historico.push_back(linha);
        }
        arquivo.close();
    }
    return historico;
}

// Salva histórico
void salvarHistorico(const std::deque<std::string>& historico) {
    std::ofstream arquivo(ARQUIVO_HISTORICO);
    if (arquivo.is_open()) {
        for (const auto& nome : historico) {
            arquivo << nome << "\n";
        }
        arquivo.close();
    }
}

int main() {
    setlocale(LC_ALL, "Portuguese"); // Tenta acentuação
    std::string caminhoOrigem, caminhoDestino;

    std::cout << "=== SELECIONADOR DE FOTOS (Versao Compativel) ===\n\n";
    std::cout << "DICA: No Windows, use barras normais (/) ou duplas (\\\\) nos caminhos.\n";
    
    std::cout << "Digite o caminho da pasta de ORIGEM: ";
    std::getline(std::cin, caminhoOrigem);

    std::cout << "Digite o caminho da pasta de DESTINO: ";
    std::getline(std::cin, caminhoDestino);

    // Remove aspas se o usuário arrastou a pasta
    caminhoOrigem.erase(remove(caminhoOrigem.begin(), caminhoOrigem.end(), '\"'), caminhoOrigem.end());
    caminhoDestino.erase(remove(caminhoDestino.begin(), caminhoDestino.end(), '\"'), caminhoDestino.end());

    // 1. Listar arquivos usando dirent.h (método antigo)
    std::vector<std::string> todasImagens;
    DIR *dir;
    struct dirent *ent;

    if ((dir = opendir(caminhoOrigem.c_str())) != NULL) {
        while ((ent = readdir(dir)) != NULL) {
            std::string nomeArquivo = ent->d_name;
            // Ignora . e .. e verifica extensão
            if (nomeArquivo != "." && nomeArquivo != ".." && ehImagem(nomeArquivo)) {
                todasImagens.push_back(nomeArquivo);
            }
        }
        closedir(dir);
    } else {
        std::cerr << "[ERRO] Nao foi possivel abrir a pasta de origem.\n";
        system("pause");
        return 1;
    }

    std::cout << "Encontradas " << todasImagens.size() << " imagens.\n";

    if (todasImagens.size() < QTD_SELECAO) {
        std::cerr << "[ERRO] A pasta tem menos de " << QTD_SELECAO << " fotos.\n";
        system("pause");
        return 1;
    }

    // 2. Filtrar e Sortear
    std::deque<std::string> historico = carregarHistorico();
    std::vector<std::string> candidatas;

    for (const auto& img : todasImagens) {
        bool jaUsada = false;
        for (const auto& h : historico) {
            if (h == img) { jaUsada = true; break; }
        }
        if (!jaUsada) candidatas.push_back(img);
    }

    if (candidatas.size() < QTD_SELECAO) {
        std::cout << "[AVISO] Poucas fotos novas. Resetando filtro.\n";
        candidatas = todasImagens;
    }

    std::random_device rd;
    std::mt19937 g(rd());
    std::shuffle(candidatas.begin(), candidatas.end(), g);

    // 3. Copiar
    int sucesso = 0;
    std::cout << "Copiando arquivos...\n";

    int limite = std::min((int)candidatas.size(), QTD_SELECAO);
    for (int i = 0; i < limite; i++) {
        std::string nome = candidatas[i];
        
        // Monta caminhos manualmente (adiciona a barra / se precisar)
        std::string srcPath = caminhoOrigem + (caminhoOrigem.back() == '\\' ? "" : "\\") + nome;
        std::string dstPath = caminhoDestino + (caminhoDestino.back() == '\\' ? "" : "\\") + nome;

        if (copiarArquivo(srcPath, dstPath)) {
            historico.push_back(nome);
            sucesso++;
        } else {
            std::cerr << "Erro ao copiar: " << nome << "\n";
        }
    }

    // Atualiza Histórico
    while (historico.size() > TAMANHO_HISTORICO) historico.pop_front();
    salvarHistorico(historico);

    std::cout << "\n--- SUCESSO! ---\n";
    std::cout << sucesso << " fotos copiadas.\n";
    system("pause");
    return 0;
}