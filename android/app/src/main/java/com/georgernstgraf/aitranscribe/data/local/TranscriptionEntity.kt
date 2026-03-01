package com.georgernstgraf.aitranscribe.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.time.LocalDateTime

@Entity(tableName = "transcriptions")
data class TranscriptionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val originalText: String,
    val processedText: String?,
    val audioFilePath: String?,
    val createdAt: String,
    val postProcessingType: String?,
    val status: String,
    val errorMessage: String?,
    val playedCount: Int = 0,
    val retryCount: Int = 0
)