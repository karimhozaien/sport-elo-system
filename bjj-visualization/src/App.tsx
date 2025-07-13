import { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement,
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import './App.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  LineElement,
  PointElement
);

interface Fighter {
  Fighter: string;
  Peak_Elo: number;
  Peak_Elo_Year: number;
  Current_Elo: number;
  Matches: number;
}

interface YearlyData {
  Year: number;
  Rank: number;
  Fighter: string;
  Elo: number;
}

function App() {
  const [fighters, setFighters] = useState<Fighter[]>([]);
  const [yearlyData, setYearlyData] = useState<YearlyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState<number>(2025);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        // Load fighters data
        const fightersResponse = await fetch('/elo_ratings.csv');
        const fightersText = await fightersResponse.text();
        const fightersData = parseCSV(fightersText);
        setFighters(fightersData);

        // Load yearly data
        const yearlyResponse = await fetch('/top3_by_year.csv');
        const yearlyText = await yearlyResponse.text();
        const yearlyData = parseCSV(yearlyText);
        
        // Debug: Log 2018 data
        const year2018Data = yearlyData.filter(d => d.Year === 2018);
        console.log('Parsed 2018 data:', year2018Data);
        
        setYearlyData(yearlyData);
      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const parseCSV = (csvText: string): any[] => {
    const lines = csvText.split('\n');
    const headers = lines[0].split(',');
    return lines.slice(1).map(line => {
      // Handle quoted values properly
      const values: string[] = [];
      let current = '';
      let inQuotes = false;
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          values.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      values.push(current.trim());
      
      const obj: any = {};
      headers.forEach((header, index) => {
        let value = values[index]?.trim() || '';
        // Clean up fighter names (remove | characters and extra quotes)
        if (header.trim() === 'Fighter') {
          value = value.replace(/\|/g, '').replace(/"/g, '').trim();
        }
        // Convert numeric fields
        if (['Peak_Elo', 'Current_Elo', 'Matches', 'Year', 'Rank', 'Elo'].includes(header.trim())) {
          obj[header.trim()] = parseFloat(value) || 0;
        } else {
          obj[header.trim()] = value;
        }
      });
      return obj;
    }).filter(row => row.Fighter && row.Fighter !== '');
  };

  const top20Fighters = fighters.slice(0, 20);
  const filteredFighters = fighters.filter(fighter =>
    fighter.Fighter.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Get available years for selection
  const availableYears = [...new Set(yearlyData.map(d => d.Year))].sort((a, b) => b - a);
  
  // Get top 3 for selected year
  const yearData = yearlyData.filter(d => d.Year === selectedYear);
  const uniqueFighters = yearData.reduce((acc, current) => {
    // Clean fighter name by removing trailing characters like "|"
    const cleanName = current.Fighter.replace(/\s*[|]\s*$/, '').trim();
    
    // Check if we already have this fighter (by cleaned name)
    const existingIndex = acc.findIndex(item => 
      item.Fighter.replace(/\s*[|]\s*$/, '').trim() === cleanName
    );
    
    if (existingIndex === -1) {
      // Add new fighter
      acc.push(current);
    } else {
      // Replace with higher ranked entry (lower rank number)
      if (current.Rank < acc[existingIndex].Rank) {
        acc[existingIndex] = current;
      }
    }
    
    return acc;
  }, [] as YearlyData[]);
  
  // Sort by rank and take top 3
  const top3ForYear = uniqueFighters
    .sort((a, b) => a.Rank - b.Rank)
    .slice(0, 3);

  const barChartData = {
    labels: top20Fighters.map(f => f.Fighter),
    datasets: [
      {
        label: 'Current Elo Rating',
        data: top20Fighters.map(f => f.Current_Elo),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1,
      },
      {
        label: 'Peak Elo Rating',
        data: top20Fighters.map(f => f.Peak_Elo),
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1,
      }
    ]
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Top 20 BJJ Fighters - Current vs Peak Elo Ratings',
        font: {
          size: 16,
          weight: 'bold' as const
        }
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Elo Rating'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Fighter'
        }
      }
    }
  };

  // Prepare yearly trends data with fighter names for tooltips
  const years = [...new Set(yearlyData.map(d => d.Year))].sort();
  
  // Create data with both Elo ratings and fighter names
  const getYearlyData = (rank: number) => {
    return years.map(year => {
      const yearData = yearlyData.filter(d => d.Year === year);
      const sortedFighters = yearData.sort((a, b) => a.Rank - b.Rank).slice(0, 3);
      const fighter = sortedFighters.find(d => d.Rank === rank);
      return fighter ? { elo: fighter.Elo, fighter: fighter.Fighter } : null;
    });
  };

  const yearlyTrendsData = {
    labels: years,
    datasets: [
      {
        label: 'Rank 1',
        data: getYearlyData(1).map(item => item?.elo || null),
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.1
      },
      {
        label: 'Rank 2',
        data: getYearlyData(2).map(item => item?.elo || null),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.1
      },
      {
        label: 'Rank 3',
        data: getYearlyData(3).map(item => item?.elo || null),
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.1
      }
    ]
  };

  // Store fighter names for tooltips
  const yearlyFighterNames = {
    rank1: getYearlyData(1).map(item => item?.fighter || ''),
    rank2: getYearlyData(2).map(item => item?.fighter || ''),
    rank3: getYearlyData(3).map(item => item?.fighter || '')
  };

  // Prepare average Elo data
  const averageEloData = {
    labels: years,
    datasets: [
      {
        label: 'Average Elo Rating',
        data: years.map(year => {
          const yearFighters = yearlyData.filter(d => d.Year === year);
          if (yearFighters.length === 0) return null;
          const average = yearFighters.reduce((sum, f) => sum + f.Elo, 0) / yearFighters.length;
          return Math.round(average * 10) / 10;
        }),
        borderColor: 'rgb(168, 85, 247)',
        backgroundColor: 'rgba(168, 85, 247, 0.1)',
        tension: 0.1,
        fill: true
      }
    ]
  };

  const averageEloOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Average Elo Rating by Year',
        font: {
          size: 16,
          weight: 'bold' as const
        }
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Average Elo Rating'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Year'
        }
      }
    }
  };

  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Yearly Top 3 Elo Ratings Trends',
        font: {
          size: 16,
          weight: 'bold' as const
        }
      },
      tooltip: {
        callbacks: {
          afterLabel: function(context: any) {
            const yearIndex = context.dataIndex;
            const datasetIndex = context.datasetIndex;
            
            let fighterName = '';
            if (datasetIndex === 0) {
              fighterName = yearlyFighterNames.rank1[yearIndex];
            } else if (datasetIndex === 1) {
              fighterName = yearlyFighterNames.rank2[yearIndex];
            } else if (datasetIndex === 2) {
              fighterName = yearlyFighterNames.rank3[yearIndex];
            }
            
            return fighterName ? `Fighter: ${fighterName}` : '';
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Elo Rating'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Year'
        }
      }
    }
  };



  const FighterImage = ({ fighterName }: { fighterName: string }) => {
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);
    const [currentImageIndex, setCurrentImageIndex] = useState(0);
    
    // Create multiple variations of the name to try different filename patterns
    const imageVariations = [
      // Original name with hyphens
      fighterName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9\-]/g, ''),
      // Name with accented characters preserved
      fighterName.toLowerCase().replace(/\s+/g, '-'),
      // Name with diacritics removed
      fighterName.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, '-'),
      // Simple lowercase with hyphens
      fighterName.toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-')
    ];
    
    const currentImageSrc = `/images/${imageVariations[currentImageIndex]}.png`;

    const handleImageError = () => {
      if (currentImageIndex < imageVariations.length - 1) {
        // Try next variation
        setCurrentImageIndex(currentImageIndex + 1);
      } else {
        // All variations failed, show placeholder
        setImageError(true);
      }
    };

    const handleImageLoad = () => {
      setImageLoaded(true);
    };

    return (
      <div className="fighter-image">
        <img 
          src={currentImageSrc} 
          alt={fighterName}
          onLoad={handleImageLoad}
          onError={handleImageError}
          style={{ display: imageError ? 'none' : 'block' }}
        />
        {(!imageLoaded && !imageError) && (
          <div className="fighter-placeholder">
            {fighterName.charAt(0)}
          </div>
        )}
        {imageError && (
          <div className="fighter-placeholder">
            {fighterName.charAt(0)}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="loading">
        <h2>Loading BJJ Elo Ratings Dashboard...</h2>
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="header">
        <h1>Karim Hozaien's Jiu-Jitsu Elo Dashboard</h1>
        <p>Comprehensive analysis of Brazilian Jiu-Jitsu fighter performance</p>
      </header>

      <div className="stats-container">
        <div className="stat-card">
          <h3>{fighters.length}</h3>
          <p>Total Fighters</p>
        </div>
        <div className="stat-card">
          <h3>{Math.max(...fighters.map(f => f.Current_Elo)).toFixed(0)}</h3>
          <p>Highest Rating</p>
        </div>
        <div className="stat-card">
          <h3>{Math.round(fighters.reduce((sum, f) => sum + f.Matches, 0) / fighters.length)}</h3>
          <p>Avg Matches</p>
        </div>
        <div className="stat-card">
          <h3>{Math.round(fighters.reduce((sum, f) => sum + f.Current_Elo, 0) / fighters.length)}</h3>
          <p>Avg Rating</p>
        </div>
      </div>

      <div className="search-section">
        <input
          type="text"
          placeholder="Search fighters..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="charts-container">
        <div className="chart-section">
          <h2>Top 20 Current Fighters</h2>
          <div className="chart-wrapper">
            <Bar data={barChartData} options={barChartOptions} />
          </div>
        </div>

        <div className="chart-section">
          <h2>Average Elo Rating by Year</h2>
          <div className="chart-wrapper">
            <Line data={averageEloData} options={averageEloOptions} />
          </div>
        </div>
      </div>

      <div className="yearly-section">
        <div className="year-selector">
          <h2>Top 3 Fighters by Year</h2>
          <select 
            value={selectedYear} 
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            className="year-select"
          >
            {availableYears.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
        
        <div className="top3-grid">
          {top3ForYear.map((fighter, index) => (
            <div key={index} className="fighter-card">
              <FighterImage fighterName={fighter.Fighter} />
              <div className="fighter-info">
                <h3>#{fighter.Rank} - {fighter.Fighter}</h3>
                <p className="elo-rating">{fighter.Elo.toFixed(1)} Elo</p>
                <p className="year">{fighter.Year}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="chart-section">
        <h2>Yearly Top 3 Trends</h2>
        <div className="chart-wrapper">
          <Line data={yearlyTrendsData} options={lineChartOptions} />
        </div>
      </div>

      <div className="explanation-section">
        <h2>How Elo Ratings Work</h2>
        <div className="explanation-content">
          <div className="explanation-card">
            <h3>What is the Elo System?</h3>
            <p>
              The Elo rating system was originally developed for chess by Arpad Elo in the 1960s. 
              It's a method for calculating relative skill levels that can be applied to any competitive activity, 
              including Brazilian Jiu-Jitsu. The system provides a numerical rating that represents a fighter's 
              relative strength compared to other competitors.
            </p>
          </div>
          
          <div className="explanation-card">
            <h3>The Mathematics</h3>
            <p>
              <strong>Expected Score:</strong> Before each match, the system calculates the expected probability 
              of winning based on the difference between the two fighters' ratings:
            </p>
            <div className="math-formula">
              <p>E = 1 / (1 + 10^((R₂ - R₁) / 400))</p>
            </div>
            <p>
              Where E is the expected score, R₁ is your rating, and R₂ is your opponent's rating.
            </p>
          </div>
          
          <div className="explanation-card">
            <h3>Rating Updates</h3>
            <p>
              After each match, ratings are updated using this formula:
            </p>
            <div className="math-formula">
              <p>R' = R + K(S - E)</p>
            </div>
            <p>
              Where R' is the new rating, R is the old rating, K is the K-factor (determines how much 
              a single match affects the rating), S is the actual score (1 for win, 0.5 for draw, 0 for loss), 
              and E is the expected score.
            </p>
          </div>
          
          <div className="explanation-card">
            <h3>Key Concepts</h3>
            <ul>
              <li><strong>K-Factor:</strong> Higher K-factors mean ratings change more dramatically with each match</li>
              <li><strong>Rating Difference:</strong> A 400-point difference means the higher-rated fighter is expected to win 90% of the time</li>
              <li><strong>Peak vs Current:</strong> Peak Elo shows the highest rating achieved, while Current Elo reflects recent performance</li>
              <li><strong>Match Count:</strong> More matches generally lead to more stable and accurate ratings</li>
            </ul>
          </div>
        </div>
      </div>

      {searchTerm && (
        <div className="search-results">
          <h2>Search Results</h2>
          <div className="fighters-grid">
            {filteredFighters.slice(0, 20).map((fighter, index) => (
              <div key={index} className="fighter-card">
                <FighterImage fighterName={fighter.Fighter} />
                <div className="fighter-info">
                  <h3>{fighter.Fighter}</h3>
                  <p><strong>Current:</strong> {fighter.Current_Elo}</p>
                  <p><strong>Peak:</strong> {fighter.Peak_Elo} ({fighter.Peak_Elo_Year})</p>
                  <p><strong>Matches:</strong> {fighter.Matches}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
