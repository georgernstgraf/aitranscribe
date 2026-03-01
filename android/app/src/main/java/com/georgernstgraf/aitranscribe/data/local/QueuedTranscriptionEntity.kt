package com.georgernstgraf.aitranscribe.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.time.LocalDateTime

@Entity(tableName = "queued_transcriptions")
data class QueuedTranscriptionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val audioFilePath: String,
    val sttModel: String,
    val llmModel: String?,
    val postProcessingType: String?,
    val createdAt: String,
    val priority: Int = 0
)